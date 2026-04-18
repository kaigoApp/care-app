from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")


class AIServiceError(Exception):
    pass


def _ai_disabled_by_policy() -> bool:
    return os.environ.get("CARE_APP_DISABLE_AI", "").strip().lower() in {"1", "true", "yes", "on"}


def _normalize_model_name(model: Optional[str] = None) -> str:
    return (model or os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL).strip()


def _looks_like_placeholder_api_key(api_key: str) -> bool:
    lowered = api_key.strip().lower()
    return lowered in {
        "",
        "your-api-key",
        "your_openai_api_key",
        "openai_api_key",
        "sk-xxxx",
        "sk-your-key",
        "あなたのapiキー",
    }


def _friendly_api_error_message(exc: Exception, model_name: str) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    lowered = text.lower()

    if any(token in lowered for token in ("incorrect api key", "invalid_api_key", "authentication", "401", "unauthorized")):
        return "APIキーが無効、または権限が不足しています。OPENAI_API_KEY を再確認してください。"
    if any(token in lowered for token in ("quota", "insufficient_quota", "billing", "rate limit", "429")):
        return "OpenAI 側の利用上限、課金設定、またはレート制限により失敗しました。"
    if any(token in lowered for token in ("model", "not found", "does not exist", "unknown model")):
        return f"モデル '{model_name}' が利用できない可能性があります。OPENAI_MODEL を確認してください。"
    if any(token in lowered for token in ("timeout", "timed out", "connection", "network")):
        return "通信タイムアウト、またはネットワーク接続の問題で失敗しました。"
    return f"OpenAI API 呼び出しに失敗しました: {text}"


def _load_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key or _looks_like_placeholder_api_key(api_key):
        raise AIServiceError(
            "OPENAI_API_KEY が未設定、または仮の値のままです。Windows のコマンド例: setx OPENAI_API_KEY \"あなたのAPIキー\""
        )

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise AIServiceError(
            "openai パッケージが見つかりません。まず 'pip install openai' を実行してください。"
        ) from exc

    try:
        return OpenAI(api_key=api_key)
    except Exception as exc:  # pragma: no cover - defensive
        raise AIServiceError(f"OpenAI クライアント初期化に失敗しました: {exc}") from exc


def get_ai_status() -> Dict[str, str]:
    if _ai_disabled_by_policy():
        return {
            "available": "false",
            "label": "停止中",
            "message": "現場テスト向けに AI 機能を停止しています。",
        }

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model_name = _normalize_model_name()

    if not api_key or _looks_like_placeholder_api_key(api_key):
        return {
            "available": "false",
            "label": "未設定",
            "message": "APIキー未設定です。OPENAI_API_KEY を設定してください。",
        }

    try:
        import openai  # noqa: F401
    except ImportError:
        return {
            "available": "false",
            "label": "要インストール",
            "message": "openai パッケージが未インストールです。pip install openai を実行してください。",
        }

    return {
        "available": "true",
        "label": "利用可能",
        "message": f"ボタンは利用可能です。実行時は OpenAI API へ接続します。使用モデル: {model_name}",
    }


def _format_context_lines(items: List[Dict[str, Any]], fields: List[str]) -> List[str]:
    lines: List[str] = []
    for item in items:
        chunks: List[str] = []
        for field in fields:
            value = item.get(field)
            if value is None or str(value).strip() == "":
                continue
            chunks.append(f"{field}={value}")
        if chunks:
            lines.append(" / ".join(chunks))
    return lines


def build_support_progress_prompt(context: Dict[str, Any]) -> str:
    resident = context.get("resident") or {}
    vitals = context.get("vitals") or []
    daily_records = context.get("daily_records") or []
    existing_records = context.get("support_progress_records") or []

    vital_lines = _format_context_lines(
        vitals,
        ["recorded_at", "scene", "temperature", "systolic_bp", "diastolic_bp", "pulse", "spo2", "note", "staff_name"],
    )
    daily_lines = _format_context_lines(
        daily_records,
        ["recorded_at", "category", "content", "staff_name"],
    )
    progress_lines = _format_context_lines(
        existing_records,
        ["recorded_at", "category", "content", "staff_name"],
    )

    payload = {
        "target_date": context.get("target_date"),
        "resident": {
            "name": resident.get("name") or "",
            "unit_name": resident.get("unit_name") or "",
            "diagnosis": resident.get("diagnosis") or "",
            "care_level": resident.get("care_level") or "",
        },
        "vitals": vital_lines,
        "daily_records": daily_lines,
        "existing_support_progress_records": progress_lines,
    }

    return json.dumps(payload, ensure_ascii=False, indent=2)


SYSTEM_PROMPT = """
あなたは障害福祉・共同生活援助の現場で使う記録文作成アシスタントです。
目的は、入力済みの事実から「支援経過記録の下書き」を日本語で作ることです。

必ず守ること:
- 事実だけを書く。入力にない出来事を作らない。
- 診断・医学的判断・断定的な評価はしない。
- 推測表現を避け、客観的な記録文にする。
- 既存の支援経過と重複しすぎる場合は簡潔にまとめる。
- 出力はそのまま記録欄に貼れる自然な日本語の本文のみ。
- 見出し、箇条書き、前置き、注意書き、JSON は出さない。
- 文章量は 2〜5 文程度。長すぎない。
- できるだけ「本日」「〜された」「〜確認」「〜記録」など、記録向けの表現にする。
""".strip()


USER_PROMPT_TEMPLATE = """
以下は、対象利用者の当日記録データです。
この内容だけを使って、支援経過記録の下書きを日本語で作成してください。

{context_json}
""".strip()


def _has_usable_context(context: Dict[str, Any]) -> bool:
    return any(
        bool(context.get(key))
        for key in ("vitals", "daily_records", "support_progress_records")
    )


def _extract_response_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    output_items = getattr(response, "output", None) or []
    fragments: List[str] = []
    for item in output_items:
        contents = getattr(item, "content", None) or []
        for content in contents:
            candidate = getattr(content, "text", None)
            if isinstance(candidate, str) and candidate.strip():
                fragments.append(candidate.strip())
    if fragments:
        return "\n".join(fragments).strip()

    try:
        response_dict = response.model_dump()  # type: ignore[attr-defined]
    except Exception:
        response_dict = None

    if isinstance(response_dict, dict):
        output_items = response_dict.get("output") or []
        for item in output_items:
            for content in item.get("content") or []:
                candidate = content.get("text")
                if isinstance(candidate, str) and candidate.strip():
                    fragments.append(candidate.strip())
    return "\n".join(fragments).strip()


def generate_support_progress_draft(context: Dict[str, Any], model: Optional[str] = None) -> str:
    if _ai_disabled_by_policy():
        raise AIServiceError("現場テスト向け設定により AI 機能を停止しています。")

    if not _has_usable_context(context):
        raise AIServiceError("当日の入力済み記録がありません。先にバイタル・食事・服薬・入浴・巡視などを保存してください。")

    client = _load_openai_client()
    prompt = USER_PROMPT_TEMPLATE.format(context_json=build_support_progress_prompt(context))
    model_name = _normalize_model_name(model)

    try:
        response = client.responses.create(
            model=model_name,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": SYSTEM_PROMPT}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                },
            ],
        )
    except Exception as exc:
        raise AIServiceError(_friendly_api_error_message(exc, model_name)) from exc

    output_text = _extract_response_text(response)
    if not output_text:
        raise AIServiceError(
            "AIの応答本文を取得できませんでした。openai パッケージが古い場合は更新してください。例: pip install -U openai"
        )
    return output_text
