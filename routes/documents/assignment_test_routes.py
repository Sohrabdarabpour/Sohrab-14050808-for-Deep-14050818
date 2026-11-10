"""صفحه‌ی تست ارجاع — فقط در حالت DEBUG.

آدرس: /documents/assignment-test-page/<document_id>
"""

from flask import abort, render_template_string, session

from config import Config

from .documents_routes import documents_bp


_TEST_PAGE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="csrf-token" content="{{ csrf_token() }}">
  <title>تست ارجاع سند #{{ doc_id }}</title>
  <style>
    body { font-family: Tahoma, sans-serif; background: #f5f7fa; padding: 20px; }
    .card { background: #fff; border-radius: 8px; padding: 16px;
            margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
    h2 { margin-top: 0; color: #1b698b; }
    label { display: block; margin: 6px 0 2px; font-weight: 600; }
    input, select, textarea { width: 100%; padding: 6px; border: 1px solid #ddd;
            border-radius: 4px; box-sizing: border-box; margin-bottom: 8px; }
    textarea { min-height: 60px; font-family: inherit; }
    button { padding: 8px 16px; border: none; background: #1b698b;
            color: #fff; border-radius: 4px; cursor: pointer; }
    button:hover { background: #145272; }
    .secondary { background: #718096; }
    .danger { background: #dc2626; }
    .msg { padding: 10px; border-radius: 4px; margin: 8px 0; }
    .msg-ok { background: #c6f6d5; color: #22543d; }
    .msg-err { background: #fed7d7; color: #742a2a; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 6px; text-align: right; border-bottom: 1px solid #eee; }
    th { background: #f7fafc; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 10px;
            font-size: 12px; background: #e2e8f0; }
    .users-list label { display: flex; gap: 6px; align-items: center;
            font-weight: normal; margin: 0; }
    .users-list input[type=checkbox] { width: auto; margin: 0; }
  </style>
</head>
<body>
  <div class="card">
    <h2>تست ارجاع سند #{{ doc_id }}</h2>
    <p>این صفحه فقط در حالت DEBUG در دسترس است.</p>
    <p>می‌توانید سند را به یک یا چند کاربر ارجاع دهید و نتیجه را در کارتابل ببینید.</p>
  </div>

  <div class="card">
    <h2>فرم ارجاع</h2>
    <form id="route-form">
      <label>گیرندگان</label>
      <div class="users-list">
        {% for u in users %}
          <label>
            <input type="checkbox" name="to_user_ids" value="{{ u.id }}">
            {{ u.full_name }} <span class="badge">{{ u.role }}</span>
          </label>
        {% endfor %}
      </div>

      <label>دستور / توضیح</label>
      <textarea name="instruction" placeholder="اختیاری..."></textarea>

      <label>مهلت اقدام (روز کاری)</label>
      <input type="number" name="due_days" value="3" min="0" max="365">

      <label>اولویت</label>
      <select name="priority">
        <option value="low">کم</option>
        <option value="normal" selected>معمولی</option>
        <option value="high">بالا</option>
        <option value="urgent">فوری</option>
      </select>

      <button type="submit">ارجاع</button>
      <a href="/inbox/"><button type="button" class="secondary">رفتن به کارتابل</button></a>
    </form>
    <div id="result"></div>
  </div>

  <div class="card">
    <h2>ارجاع‌های فعلی این سند</h2>
    <div id="assignments-area">در حال بارگذاری...</div>
  </div>

<script>
const DOC_ID = {{ doc_id }};
const CSRF = document.querySelector('meta[name="csrf-token"]').content;

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
}

async function loadAssignments() {
  const area = document.getElementById('assignments-area');
  try {
    const res = await fetch(`/documents/${DOC_ID}/assignments.json`);
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || 'خطا');
    if (!data.assignments.length) {
      area.textContent = 'هنوز ارجاعی برای این سند ثبت نشده است.';
      return;
    }
    let html = '<table><thead><tr>'
      + '<th>#</th><th>از</th><th>به</th><th>وضعیت</th>'
      + '<th>مهلت</th><th>خوانده</th>'
      + '</tr></thead><tbody>';
    for (const a of data.assignments) {
      html += `<tr>
        <td>${a.id}</td>
        <td>${escapeHtml(a.from_user_name || '—')}</td>
        <td>${escapeHtml(a.to_user_name || '—')}</td>
        <td><span class="badge">${escapeHtml(a.status)}</span></td>
        <td>${escapeHtml(a.due_date || '—')}</td>
        <td>${a.read_at ? '✓' : '—'}</td>
      </tr>`;
    }
    html += '</tbody></table>';
    area.innerHTML = html;
  } catch (e) {
    area.innerHTML = `<div class="msg msg-err">خطا: ${escapeHtml(e.message)}</div>`;
  }
}

document.getElementById('route-form').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const form = ev.target;
  const toIds = Array.from(form.querySelectorAll('input[name="to_user_ids"]:checked'))
                      .map(c => parseInt(c.value));
  if (!toIds.length) {
    document.getElementById('result').innerHTML =
      '<div class="msg msg-err">حداقل یک گیرنده انتخاب کنید</div>';
    return;
  }
  const body = {
    to_user_ids: toIds,
    instruction: form.querySelector('textarea[name="instruction"]').value || null,
    due_days: parseInt(form.querySelector('input[name="due_days"]').value || '3'),
    priority: form.querySelector('select[name="priority"]').value,
  };
  try {
    const res = await fetch(`/documents/${DOC_ID}/route`, {
      method: 'POST',
      headers: {'Content-Type':'application/json', 'X-CSRFToken': CSRF},
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!data.ok) throw new Error(data.message || data.error || 'خطا');
    const created = (data.created || []).map(c =>
      `${escapeHtml(c.to_user_name)} (مهلت: ${escapeHtml(c.due_date)})`
    ).join('، ');
    document.getElementById('result').innerHTML =
      `<div class="msg msg-ok">✅ ارجاع ثبت شد: ${created}</div>`;
    loadAssignments();
  } catch (e) {
    document.getElementById('result').innerHTML =
      `<div class="msg msg-err">خطا: ${escapeHtml(e.message)}</div>`;
  }
});

loadAssignments();
</script>
</body>
</html>
"""


@documents_bp.route(
    "/assignment-test-page/<int:document_id>", methods=["GET"]
)
def assignment_test_page(document_id):
    """صفحه‌ی تست ارجاع — فقط DEBUG."""
    if not Config.DEBUG:
        abort(404)
    if not session.get("user_id"):
        abort(401)

    from database.connection import get_connection
    conn = get_connection()
    try:
        users = [
            dict(r) for r in conn.execute(
                "SELECT id, full_name, role FROM users "
                "WHERE is_active = 1 ORDER BY full_name"
            ).fetchall()
        ]
    finally:
        conn.close()

    return render_template_string(
        _TEST_PAGE, doc_id=document_id, users=users
    )