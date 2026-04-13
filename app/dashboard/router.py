from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.db.database import SessionLocal
from app.db.models import Review, Finding
from sqlalchemy import func

router = APIRouter()

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    db = SessionLocal()

    reviews = db.query(Review).order_by(Review.created_at.desc()).all()

    total_reviews = len(reviews)
    total_findings = db.query(func.sum(Review.total_findings)).scalar() or 0
    total_tokens_in = db.query(func.sum(Review.tokens_in)).scalar() or 0
    total_tokens_out = db.query(func.sum(Review.tokens_out)).scalar() or 0

    # Cost estimate — OpenRouter free tier is $0 but use standard pricing for display
    estimated_cost = round((total_tokens_in * 0.000001) + (total_tokens_out * 0.000002), 4)

    findings_by_severity = {
        "error": db.query(Finding).filter(Finding.severity == "error").count(),
        "warning": db.query(Finding).filter(Finding.severity == "warning").count(),
        "style": db.query(Finding).filter(Finding.severity == "style").count(),
    }

    findings_by_category = {
        "security": db.query(Finding).filter(Finding.category == "security").count(),
        "logic": db.query(Finding).filter(Finding.category == "logic").count(),
        "performance": db.query(Finding).filter(Finding.category == "performance").count(),
        "style": db.query(Finding).filter(Finding.category == "style").count(),
    }

    db.close()

    rows = ""
    for r in reviews:
        status_color = "#22c55e" if r.status == "completed" else "#ef4444" if r.status == "failed" else "#f59e0b"
        rows += f"""
        <tr>
            <td>{r.id}</td>
            <td>{r.owner}/{r.repo}</td>
            <td>#{r.pull_number}</td>
            <td><span style="color:{status_color};font-weight:600">{r.status}</span></td>
            <td>{r.total_findings}</td>
            <td>{r.tokens_in + r.tokens_out}</td>
            <td>{r.created_at.strftime('%Y-%m-%d %H:%M')}</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Code Review Agent — Dashboard</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d1117; color: #e6edf3; min-height: 100vh; padding: 32px; }}
            h1 {{ font-size: 24px; font-weight: 700; margin-bottom: 8px; }}
            .subtitle {{ color: #8b949e; margin-bottom: 32px; font-size: 14px; }}
            .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px; }}
            .stat-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; }}
            .stat-label {{ font-size: 12px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }}
            .stat-value {{ font-size: 32px; font-weight: 700; }}
            .stat-value.red {{ color: #f85149; }}
            .stat-value.yellow {{ color: #d29922; }}
            .stat-value.blue {{ color: #388bfd; }}
            .stat-value.green {{ color: #3fb950; }}
            .section {{ background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 24px; margin-bottom: 24px; }}
            .section h2 {{ font-size: 16px; font-weight: 600; margin-bottom: 20px; color: #e6edf3; }}
            .bars {{ display: flex; flex-direction: column; gap: 12px; }}
            .bar-row {{ display: flex; align-items: center; gap: 12px; }}
            .bar-label {{ width: 100px; font-size: 13px; color: #8b949e; text-transform: capitalize; }}
            .bar-track {{ flex: 1; background: #21262d; border-radius: 4px; height: 8px; }}
            .bar-fill {{ height: 8px; border-radius: 4px; }}
            .bar-count {{ width: 30px; font-size: 13px; text-align: right; color: #e6edf3; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ text-align: left; padding: 12px 16px; font-size: 12px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #30363d; }}
            td {{ padding: 12px 16px; font-size: 14px; border-bottom: 1px solid #21262d; }}
            tr:last-child td {{ border-bottom: none; }}
            tr:hover td {{ background: #1c2128; }}
        </style>
    </head>
    <body>
        <h1>🤖 Code Review Agent</h1>
        <p class="subtitle">Real-time dashboard — AI-powered pull request analysis</p>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">Total Reviews</div>
                <div class="stat-value blue">{total_reviews}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Findings</div>
                <div class="stat-value yellow">{total_findings}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Errors Found</div>
                <div class="stat-value red">{findings_by_severity['error']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Tokens Used</div>
                <div class="stat-value green">{total_tokens_in + total_tokens_out:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Est. Cost</div>
                <div class="stat-value">${estimated_cost}</div>
            </div>
        </div>

        <div class="section">
            <h2>Findings by Severity</h2>
            <div class="bars">
                <div class="bar-row">
                    <span class="bar-label">Errors</span>
                    <div class="bar-track"><div class="bar-fill" style="width:{min(findings_by_severity['error'] * 10, 100)}%;background:#f85149"></div></div>
                    <span class="bar-count">{findings_by_severity['error']}</span>
                </div>
                <div class="bar-row">
                    <span class="bar-label">Warnings</span>
                    <div class="bar-track"><div class="bar-fill" style="width:{min(findings_by_severity['warning'] * 10, 100)}%;background:#d29922"></div></div>
                    <span class="bar-count">{findings_by_severity['warning']}</span>
                </div>
                <div class="bar-row">
                    <span class="bar-label">Style</span>
                    <div class="bar-track"><div class="bar-fill" style="width:{min(findings_by_severity['style'] * 10, 100)}%;background:#388bfd"></div></div>
                    <span class="bar-count">{findings_by_severity['style']}</span>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Findings by Category</h2>
            <div class="bars">
                <div class="bar-row">
                    <span class="bar-label">Security</span>
                    <div class="bar-track"><div class="bar-fill" style="width:{min(findings_by_category['security'] * 10, 100)}%;background:#f85149"></div></div>
                    <span class="bar-count">{findings_by_category['security']}</span>
                </div>
                <div class="bar-row">
                    <span class="bar-label">Logic</span>
                    <div class="bar-track"><div class="bar-fill" style="width:{min(findings_by_category['logic'] * 10, 100)}%;background:#d29922"></div></div>
                    <span class="bar-count">{findings_by_category['logic']}</span>
                </div>
                <div class="bar-row">
                    <span class="bar-label">Performance</span>
                    <div class="bar-track"><div class="bar-fill" style="width:{min(findings_by_category['performance'] * 10, 100)}%;background:#3fb950"></div></div>
                    <span class="bar-count">{findings_by_category['performance']}</span>
                </div>
                <div class="bar-row">
                    <span class="bar-label">Style</span>
                    <div class="bar-track"><div class="bar-fill" style="width:{min(findings_by_category['style'] * 10, 100)}%;background:#388bfd"></div></div>
                    <span class="bar-count">{findings_by_category['style']}</span>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Recent Reviews</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Repository</th>
                        <th>PR</th>
                        <th>Status</th>
                        <th>Findings</th>
                        <th>Tokens</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """

    return HTMLResponse(content=html)