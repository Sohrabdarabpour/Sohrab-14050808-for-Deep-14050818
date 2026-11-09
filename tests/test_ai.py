"""تست‌های بخش هوش مصنوعی (دستیار).

این تست‌ها بدون شبکه اجرا می‌شوند: LLM در fixture غیرفعال می‌شود تا
درخواست واقعی به API ارسال نشود. مسیر rule-based (intent registry) تست می‌شود.
"""

import os
import re
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.ai import AssistantService, Formatters, IntentRegistry  # noqa: E402
from services.ai.llm_config import LLMConfig  # noqa: E402
from services.ai.llm_tools import LLMTools  # noqa: E402
from services.ai.nlu import NLU  # noqa: E402


@pytest.fixture(autouse=True)
def offline_llm():
    """LLM خاموش + پاک‌سازی rate limit بین تست‌ها."""
    original = LLMConfig.ENABLED
    LLMConfig.ENABLED = False
    AssistantService._rate_store.clear()
    yield
    LLMConfig.ENABLED = original
    AssistantService._rate_store.clear()


# ============================================================
# ثبت intentها
# ============================================================
def test_intents_are_registered():
    assert IntentRegistry.count() >= 30, f"فقط {IntentRegistry.count()} intent ثبت شده"

    names = set(IntentRegistry.names())
    expected = {
        "count_all",
        "count_in_progress",
        "count_completed",
        "list_my_documents",
        "list_overdue",
        "search",
        "top_experts",
        "weekly_trend",
    }
    missing = expected - names
    assert not missing, f"intentهای انتظاری ثبت نشده‌اند: {missing}"


def test_registry_info_structure():
    info = IntentRegistry.info()
    assert info["total"] == IntentRegistry.count()
    assert all("name" in item and "priority" in item for item in info["intents"])


def test_duplicate_registration_is_rejected():
    with pytest.raises(ValueError):

        @IntentRegistry.register(name="count_all", patterns=[r"x"])
        def _duplicate(question, entities, user_id, is_admin):
            return None


# ============================================================
# تشخیص intent
# ============================================================
@pytest.mark.parametrize(
    "question,expected",
    [
        ("چند سند در حال بررسی داریم؟", "count_in_progress"),
        ("چند سند تکمیل شده؟", "count_completed"),
        ("کارهای من چیه؟", "list_my_documents"),
    ],
)
def test_detect_known_intents(question, expected):
    intent, _entities, confidence = IntentRegistry.detect(NLU.clean(question), is_admin=True)
    assert intent == expected, f"«{question}» → {intent} (انتظار: {expected})"
    assert confidence > 0


def test_detect_unknown_question():
    intent, entities, confidence = IntentRegistry.detect("قیمت بیت‌کوین چنده؟", is_admin=True)
    assert intent == "unknown"
    assert entities == {}
    assert confidence == 0.0


def test_clean_does_not_break_words_containing_fillers():
    """رگرسیون: «کمی» داخل «تکمیل» نباید حذف شود.

    باگ قبلی: clean() از replace ساده استفاده می‌کرد و «تکمیل» را به «ت ل»
    تبدیل می‌کرد؛ در نتیجه intent شمارش اسناد تکمیل‌شده هرگز تشخیص داده نمی‌شد.
    """
    assert "تکمیل" in NLU.clean("چند سند تکمیل شده؟")
    assert "تکمیل" in NLU.clean("لطفا چند سند تکمیل شده")
    # خودِ «کمی» وقتی کلمه‌ی مستقل است باید حذف شود
    assert "کمی" not in NLU.clean("کمی صبر کن").split()


def test_count_completed_detected_after_filler_cleanup():
    """مسیر کامل: جمله → clean → detect."""
    intent, _entities, _confidence = IntentRegistry.detect(
        NLU.clean("لطفا بگو چند سند تکمیل شده؟"), is_admin=True
    )
    assert intent == "count_completed"


def test_help_intent_exists():
    """رگرسیون: پیشنهاد «راهنما» باید خودش intent داشته باشد، وگرنه حلقه می‌شود."""
    assert "help" in IntentRegistry.names()

    intent, _entities, _confidence = IntentRegistry.detect(NLU.clean("راهنما"), is_admin=True)
    assert intent == "help"


def test_help_answer_lists_capabilities():
    result = AssistantService.ask("راهنما", user_id=105, is_admin=False)
    assert result["meta"]["intent"] == "help"
    assert result["type"] == "help"
    assert str(IntentRegistry.count()) in result["answer"]


def test_admin_only_intent_is_hidden_from_normal_user():
    question = "پرمشغله‌ترین کارشناس کیست؟"

    as_admin, _, _ = IntentRegistry.detect(NLU.clean(question), is_admin=True)
    as_user, _, _ = IntentRegistry.detect(NLU.clean(question), is_admin=False)

    assert as_admin == "top_experts"
    assert as_user != "top_experts", "intent ادمین نباید برای کاربر عادی قابل تشخیص باشد"


# ============================================================
# ساختار پاسخ
# ============================================================
def test_formatter_response_shape():
    result = Formatters.response("متن", "count", data=[1, 2], suggestions=["الف"])

    assert result["answer"] == "متن"
    assert result["type"] == "count"
    assert result["data"] == [1, 2]
    assert result["suggestions"] == ["الف"]
    assert "at" in result


def test_ask_returns_standard_response():
    result = AssistantService.ask("چند سند در حال بررسی داریم؟", user_id=101, is_admin=True)

    for key in ("answer", "type", "data", "suggestions", "meta"):
        assert key in result, f"کلید {key} در پاسخ نیست"

    assert result["answer"], "پاسخ خالی است"
    assert result["meta"]["intent"] == "count_in_progress"
    assert isinstance(result["meta"]["elapsed_ms"], int)
    assert result["meta"]["confidence"] > 0


def test_ask_unknown_question_returns_unknown_or_help():
    result = AssistantService.ask("یک سوال کاملاً بی‌ربط xqzwv", user_id=102, is_admin=True)

    assert result["meta"]["intent"] == "unknown"
    assert result["type"] in {"unknown", "help", "text"}
    assert result["suggestions"], "برای سوال نامفهوم باید پیشنهاد بدهد"


def test_ask_empty_question():
    result = AssistantService.ask("   ", user_id=103, is_admin=True)
    assert result["type"] == "empty"


def test_ask_truncates_long_question():
    long_question = "چند سند " * 200  # بیش از ۵۰۰ کاراکتر
    result = AssistantService.ask(long_question, user_id=104, is_admin=True, debug=True)
    assert len(result["meta"]["cleaned"]) <= 500


# ============================================================
# محدودیت نرخ
# ============================================================
def test_rate_limit_blocks_after_threshold():
    original = AssistantService.RATE_LIMIT
    AssistantService.RATE_LIMIT = 2
    try:
        assert AssistantService._check_rate_limit(555) is True
        assert AssistantService._check_rate_limit(555) is True
        assert AssistantService._check_rate_limit(555) is False
    finally:
        AssistantService.RATE_LIMIT = original


def test_rate_limit_is_per_user():
    original = AssistantService.RATE_LIMIT
    AssistantService.RATE_LIMIT = 1
    try:
        assert AssistantService._check_rate_limit(601) is True
        assert AssistantService._check_rate_limit(601) is False
        assert AssistantService._check_rate_limit(602) is True
    finally:
        AssistantService.RATE_LIMIT = original


# ============================================================
# مسیرهای HTTP
# ============================================================
def test_ping_is_public(client):
    response = client.get("/assistant/ping")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True


def test_index_requires_login(client):
    response = client.get("/assistant/")
    assert response.status_code == 302
    assert "login" in response.headers.get("Location", "").lower()


def test_ask_requires_login(client):
    """درخواست JSON بدون لاگین باید 401 بدهد (نه ریدایرکت)."""
    response = client.post("/assistant/ask", json={"question": "چند سند داریم؟"})
    assert response.status_code == 401
    assert response.get_json()["error"] == "unauthorized"


def test_ask_endpoint_returns_json(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["role"] = "admin"

    response = client.post(
        "/assistant/ask",
        json={"question": "چند سند در حال بررسی داریم؟"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["answer"]
    assert "meta" in payload


def test_ask_endpoint_rejects_empty_question(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1

    response = client.post("/assistant/ask", json={"question": "  "})
    assert response.status_code == 400
    assert response.get_json()["error"] == "empty_question"


# ============================================================
# امنیت: کلید API نباید در کد باشد
# ============================================================
def test_no_hardcoded_api_keys_in_source():
    """کلیدهای API باید فقط در .env باشند، نه در سورس."""
    ai_dir = os.path.join(PROJECT_ROOT, "services", "ai")
    pattern = re.compile(r"[\"'](sk-[a-zA-Z0-9]{10,}|aa-[a-zA-Z0-9]{20,})[\"']")
    offenders = []

    for root, dirs, files in os.walk(ai_dir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(root, name)
            with open(path, encoding="utf-8") as handle:
                for number, line in enumerate(handle, start=1):
                    if pattern.search(line):
                        offenders.append(f"{os.path.relpath(path, PROJECT_ROOT)}:{number}")

    assert not offenders, "کلید API داخل سورس پیدا شد:\n" + "\n".join(offenders)


def test_llm_config_reads_from_environment():
    """LLMConfig باید از env بخواند؛ بدون کلید، is_available باید False باشد."""
    original_key = LLMConfig.DEEPSEEK_API_KEY
    original_provider = LLMConfig.PROVIDER
    original_enabled = LLMConfig.ENABLED
    try:
        LLMConfig.PROVIDER = "deepseek"
        LLMConfig.ENABLED = True
        LLMConfig.DEEPSEEK_API_KEY = ""
        assert LLMConfig.is_available() is False
        assert LLMConfig.get_active_config() == (None, None, None)

        LLMConfig.DEEPSEEK_API_KEY = "test-key"
        assert LLMConfig.is_available() is True
        assert LLMConfig.get_active_config()[0] == "test-key"
    finally:
        LLMConfig.DEEPSEEK_API_KEY = original_key
        LLMConfig.PROVIDER = original_provider
        LLMConfig.ENABLED = original_enabled


def test_describe_hides_secret():
    description = LLMConfig.describe()
    assert "api_key" not in description
    assert set(description) >= {"provider", "enabled", "configured", "model"}


# ============================================================
# احوال‌پرسی و پروژه/پیمانکار (intentهای جدید)
# ============================================================
@pytest.mark.parametrize(
    "question,expected",
    [
        ("سلام", "greeting"),
        ("صبح بخیر", "greeting"),
        ("چطوری؟", "how_are_you"),
        ("ممنون", "thanks"),
        ("خداحافظ", "goodbye"),
        ("تو کی هستی", "who_are_you"),
        ("چند پروژه داریم؟", "count_projects"),
        ("لیست پروژه‌ها", "list_projects"),
        ("چند پیمانکار داریم", "count_contractors"),
        ("لیست پیمانکارها", "list_contractors"),
        ("نواحی", "list_areas"),
    ],
)
def test_detect_social_and_project_intents(question, expected):
    intent, _entities, _confidence = IntentRegistry.detect(NLU.clean(question), is_admin=True)
    assert intent == expected, f"«{question}» → {intent} (انتظار: {expected})"


def test_greeting_does_not_hijack_real_question():
    """«سلام» در ابتدای یک سؤال واقعی نباید کل پیام را به احوال‌پرسی ببرد."""
    intent, _entities, _confidence = IntentRegistry.detect(
        NLU.clean("سلام چند سند تکمیل شده؟"), is_admin=True
    )
    assert intent == "count_completed"


def test_project_details_needs_a_name():
    """«وضعیت پروژه X» باید به جزئیات برود، نه شمارش."""
    intent, entities, _confidence = IntentRegistry.detect(
        NLU.clean("وضعیت پروژه خط دو"), is_admin=True
    )
    assert intent == "project_details"
    assert entities.get("name")


def test_greeting_returns_friendly_answer():
    result = AssistantService.ask("سلام", user_id=1, is_admin=True)
    assert result["meta"]["intent"] == "greeting"
    assert result["type"] == "text"
    assert result["answer"]
    assert result["suggestions"]


def test_thanks_and_goodbye_respond():
    for question in ("ممنون", "خداحافظ"):
        result = AssistantService.ask(question, user_id=1, is_admin=True)
        assert result["answer"]
        assert result["type"] == "text"


def test_count_projects_returns_count():
    result = AssistantService.ask("چند پروژه داریم؟", user_id=1, is_admin=True)
    assert result["meta"]["intent"] == "count_projects"
    assert result["type"] in {"count", "text"}


def test_list_contractors_returns_list():
    result = AssistantService.ask("لیست پیمانکارها", user_id=1, is_admin=True)
    assert result["meta"]["intent"] == "list_contractors"
    assert result["type"] in {"list", "text"}


# ============================================================
# ابزارهای LLM (مسیر هوشمند)
# ============================================================
def test_llm_tools_cover_projects_and_contractors():
    tools = LLMTools.get_tools_schema(is_admin=True)
    names = {tool["function"]["name"] for tool in tools}

    expected = {
        "list_projects",
        "get_projects_summary",
        "search_projects",
        "list_contractors",
        "list_areas",
        "get_contractor_documents",
    }
    missing = expected - names
    assert not missing, f"ابزارهای LLM اضافه نشده‌اند: {missing}"


def test_llm_tool_execute_list_areas():
    result = LLMTools.execute("list_areas", {}, user_id=1, is_admin=True)
    assert "count" in result
    assert isinstance(result.get("areas"), list)


def test_llm_tool_execute_unknown_tool():
    result = LLMTools.execute("does_not_exist", {}, user_id=1, is_admin=True)
    assert "error" in result


def test_llm_tool_search_projects_requires_query():
    result = LLMTools.execute("search_projects", {}, user_id=1, is_admin=True)
    assert "error" in result
