"""
HFIP – Email Notification
Sends HTML email alerts via SMTP (Gmail app password or any SMTP server).
"""

from __future__ import annotations

import json
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from loguru import logger


class EmailNotifier:
    """
    Sends formatted HTML email alerts when a high-scoring tender is found.
    Supports Gmail (via app password) or any SMTP server.
    """

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        sender: Optional[str] = None,
        password: Optional[str] = None,
        recipients: Optional[List[str]] = None,
    ):
        self.smtp_host = smtp_host or os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.getenv("EMAIL_SMTP_PORT", "587"))
        self.sender = sender or os.getenv("EMAIL_SENDER", "")
        self.password = password or os.getenv("EMAIL_PASSWORD", "")
        raw_recipients = recipients or os.getenv("EMAIL_RECIPIENTS", "")
        if isinstance(raw_recipients, str):
            self.recipients = [r.strip() for r in raw_recipients.split(",") if r.strip()]
        else:
            self.recipients = raw_recipients

        if not self.sender or not self.password or not self.recipients:
            logger.warning("Email credentials incomplete – email notifications disabled.")

    def send(self, tender: dict, evaluation: dict) -> bool:
        """Send an HTML email alert. Returns True on success."""
        if not self.sender or not self.password or not self.recipients:
            return False

        subject = self._build_subject(tender, evaluation)
        html_body = self._build_html(tender, evaluation)
        plain_body = self._build_plain(tender, evaluation)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)
        msg.attach(MIMEText(plain_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=20) as server:
                server.ehlo()
                server.starttls()
                server.login(self.sender, self.password)
                server.sendmail(self.sender, self.recipients, msg.as_string())
            logger.info(f"Email sent to {self.recipients} for: {tender.get('title', '')[:50]}")
            return True
        except Exception as exc:
            logger.error(f"Email send failed: {exc}")
            return False

    def _build_subject(self, tender: dict, evaluation: dict) -> str:
        score = evaluation.get("score", 0)
        title = tender.get("title", "")[:70]
        return f"🚨 HFIP Alert [{score}/100] – {title}"

    def _build_html(self, tender: dict, evaluation: dict) -> str:
        title = tender.get("title", "Unknown")
        source = tender.get("source", "").upper()
        score = evaluation.get("score", 0)
        category = evaluation.get("category", "")
        summary = evaluation.get("summary", "")
        url = tender.get("url", "#")
        deadline = tender.get("deadline")
        deadline_str = deadline.strftime("%d %B %Y") if isinstance(deadline, datetime) else str(deadline or "TBC")
        skills = evaluation.get("required_skills", [])
        if isinstance(skills, str):
            try:
                skills = json.loads(skills)
            except Exception:
                skills = []
        skills_html = "".join(f'<span style="background:#e3f2fd;border-radius:4px;padding:2px 8px;margin:2px;display:inline-block">{s}</span>' for s in skills[:6])
        effort = evaluation.get("proposal_effort", "Unknown")
        consortium = "Yes" if evaluation.get("consortium_required") else "No"
        org = tender.get("organization", "Unknown")
        country = tender.get("country", "Unknown")

        return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;max-width:680px;margin:0 auto;padding:20px;color:#333">
  <div style="background:linear-gradient(135deg,#0078D4,#00BCF2);padding:20px;border-radius:8px 8px 0 0">
    <h1 style="color:white;margin:0;font-size:20px">🚨 New Healthcare AI Opportunity</h1>
    <p style="color:#e3f2fd;margin:8px 0 0">Healthcare Funding Intelligence Platform (HFIP)</p>
  </div>
  <div style="border:1px solid #ddd;border-top:none;border-radius:0 0 8px 8px;padding:24px">
    <h2 style="color:#0078D4;margin-top:0">{title}</h2>
    <table style="width:100%;border-collapse:collapse">
      <tr><td style="padding:6px 0;font-weight:bold;width:160px">Source</td><td>{source}</td></tr>
      <tr style="background:#f9f9f9"><td style="padding:6px 0;font-weight:bold">Organization</td><td>{org}</td></tr>
      <tr><td style="padding:6px 0;font-weight:bold">Country</td><td>{country}</td></tr>
      <tr style="background:#f9f9f9"><td style="padding:6px 0;font-weight:bold">Deadline</td><td><strong style="color:#d32f2f">{deadline_str}</strong></td></tr>
      <tr><td style="padding:6px 0;font-weight:bold">AI Score</td><td><strong style="font-size:18px;color:#0078D4">{score}/100</strong></td></tr>
      <tr style="background:#f9f9f9"><td style="padding:6px 0;font-weight:bold">Category</td><td>{category}</td></tr>
      <tr><td style="padding:6px 0;font-weight:bold">Proposal Effort</td><td>{effort}</td></tr>
      <tr style="background:#f9f9f9"><td style="padding:6px 0;font-weight:bold">Consortium Required</td><td>{consortium}</td></tr>
    </table>
    <h3 style="color:#333;margin-top:20px">Summary</h3>
    <p style="background:#f5f5f5;padding:12px;border-radius:4px;line-height:1.6">{summary}</p>
    <h3 style="color:#333">Required Skills</h3>
    <div style="margin-bottom:16px">{skills_html}</div>
    <a href="{url}" style="background:#0078D4;color:white;padding:12px 24px;border-radius:4px;text-decoration:none;display:inline-block;font-weight:bold">View Tender →</a>
  </div>
  <p style="color:#999;font-size:12px;margin-top:12px">This alert was generated automatically by HFIP. Do not reply to this email.</p>
</body>
</html>"""

    def _build_plain(self, tender: dict, evaluation: dict) -> str:
        title = tender.get("title", "Unknown")
        score = evaluation.get("score", 0)
        summary = evaluation.get("summary", "")
        url = tender.get("url", "")
        deadline = tender.get("deadline")
        deadline_str = deadline.strftime("%d %B %Y") if isinstance(deadline, datetime) else str(deadline or "TBC")
        skills = evaluation.get("required_skills", [])
        if isinstance(skills, str):
            try:
                skills = json.loads(skills)
            except Exception:
                skills = []
        return (
            f"NEW HEALTHCARE AI OPPORTUNITY\n\n"
            f"Title: {title}\n"
            f"Source: {tender.get('source', '').upper()}\n"
            f"Score: {score}/100\n"
            f"Deadline: {deadline_str}\n"
            f"Summary: {summary}\n"
            f"Skills: {', '.join(skills)}\n"
            f"Link: {url}\n"
        )
