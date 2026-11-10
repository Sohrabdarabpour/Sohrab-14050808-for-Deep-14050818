"""دستورات CLI — اجرا با `flask <command>` یا `python -m ...`."""

import click
from flask.cli import with_appcontext


def register_cli(app):
    """ثبت دستورات CLI روی app."""

    @app.cli.command("alarms-scan")
    @with_appcontext
    def alarms_scan():
        """اسکن همه‌ی هشدارها (ارجاع + سند) و ارسال notifications."""
        from services.documents import alarm_service
        result = alarm_service.scan_all()
        click.echo(f"✅ اسکن کامل شد")
        click.echo(f"   ارجاع‌ها: {result['assignments']['total']}")
        click.echo(f"   اسناد:   {result['documents']['total']}")
        click.echo(f"   مجموع:   {result['total_created']}")

    @app.cli.command("refresh-overdue")
    @with_appcontext
    def refresh_overdue():
        """به‌روزرسانی پرچم دیرکرد همه‌ی اسناد."""
        from services.documents import sla_service
        result = sla_service.refresh_overdue_flags()
        click.echo(f"✅ {result['total']} سند به‌روز شد")

    @app.cli.command("recalc-sla")
    @click.argument("document_id", type=int)
    @with_appcontext
    def recalc_sla(document_id):
        """محاسبه‌ی مجدد SLA یک سند."""
        from services.documents import sla_service
        result = sla_service.recalculate_sla(document_id, actor_id=None)
        if result["ok"]:
            click.echo(f"✅ مهلت: {result['sla_days']} روز ({result['sla_source']})")
            click.echo(f"   سررسید: {result['response_due_date']}")
            click.echo(f"   دیرکرد: {result['overdue_days']} روز")
        else:
            click.echo(f"❌ {result['error']}", err=True)