#!/usr/bin/env python3
import os

PROJECTS = [
    {
        "filename": "card-agentmart.svg",
        "title": "AgentMart // Multi-Agent Engine",
        "category": "AUTONOMOUS SYSTEMS • MULTI-AGENT ORCHESTRATION",
        "desc": "Autonomous multi-agent system featuring dynamic role dispatch, goal decomposition, and secure tool execution via Model Context Protocol (MCP).",
        "tags": ["Python", "LangGraph", "MCP", "FastAPI"],
        "accent": "#A855F7",
        "accent_glow": "#C084FC",
        "border": "#A855F7",
        "status": "PRODUCTION READY",
        "status_color": "#10B981",
        "icon": '<circle cx="16" cy="16" r="10" fill="none" stroke="#A855F7" stroke-width="2"/><circle cx="16" cy="16" r="4" fill="#C084FC"/><path d="M16 6v4M16 22v4M6 16h4M22 16h4" stroke="#A855F7" stroke-width="2"/>'
    },
    {
        "filename": "card-specrag.svg",
        "title": "SpecRAG // Context Engine",
        "category": "KNOWLEDGE RETRIEVAL • ENTERPRISE RAG",
        "desc": "Modular, spec-driven RAG architecture for intelligent document retrieval, multi-stage reranking, and high-precision LLM context engineering.",
        "tags": ["Python", "Hybrid Search", "VectorDB", "LangChain"],
        "accent": "#00F0FF",
        "accent_glow": "#38BDF8",
        "border": "#00F0FF",
        "status": "ACTIVE BENCHMARK",
        "status_color": "#00F0FF",
        "icon": '<rect x="6" y="6" width="20" height="20" rx="4" fill="none" stroke="#00F0FF" stroke-width="2"/><path d="M10 12h12M10 16h8M10 20h10" stroke="#00F0FF" stroke-width="1.8" stroke-linecap="round"/>'
    },
    {
        "filename": "card-aegisarm.svg",
        "title": "AegisArm // Robotics AI",
        "category": "ROBOTICS &amp; SIMULATION • PREDICTIVE AI",
        "desc": "Closed-loop robotic predictive maintenance simulator combining PyTorch deep LSTMs and PyBullet 6-DOF physics for real-time failure prevention.",
        "tags": ["PyTorch", "PyBullet", "LSTM", "Simulation"],
        "accent": "#F59E0B",
        "accent_glow": "#FCD34D",
        "border": "#F59E0B",
        "status": "TELEMETRY VERIFIED",
        "status_color": "#10B981",
        "icon": '<path d="M6 24h20M12 24V14l8-6 4 3-7 5v8" fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round"/><circle cx="16" cy="11" r="2.5" fill="#FCD34D"/>'
    },
    {
        "filename": "card-more-repos.svg",
        "title": "+36 Additional Codebases",
        "category": "ECOSYSTEM REPOSITORIES • CV &amp; FULL-STACK",
        "desc": "Explore computer vision pipelines, MCP servers, sentiment analysis, and full-stack platforms across 39 public GitHub repositories.",
        "tags": ["Computer Vision", "MCP", "PyTorch", "Full-Stack"],
        "accent": "#00F0FF",
        "accent_glow": "#38BDF8",
        "border": "#A855F7",
        "status": "CATALOG ONLINE",
        "status_color": "#00F0FF",
        "icon": '<rect x="6" y="6" width="20" height="20" rx="4" fill="none" stroke="#00F0FF" stroke-width="2"/><circle cx="16" cy="16" r="3" fill="#A855F7"/><path d="M12 16h8M16 12v8" stroke="#00F0FF" stroke-width="2" stroke-linecap="round"/>'
    }
]

card_template = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 450 190" width="100%" height="100%">
  <defs>
    <linearGradient id="cardBg_{id}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#070b19"/>
      <stop offset="60%" stop-color="#0a0f26"/>
      <stop offset="100%" stop-color="#050814"/>
    </linearGradient>
    <linearGradient id="borderGrad_{id}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{border}" stop-opacity="0.9"/>
      <stop offset="50%" stop-color="#1e293b" stop-opacity="0.4"/>
      <stop offset="100%" stop-color="{border}" stop-opacity="0.8"/>
    </linearGradient>
    <filter id="cardGlow_{id}" x="-10%" y="-10%" width="120%" height="120%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>

  <!-- Card Chassis -->
  <rect x="4" y="4" width="442" height="182" rx="14" fill="url(#cardBg_{id})" stroke="url(#borderGrad_{id})" stroke-width="1.6" filter="url(#cardGlow_{id})"/>

  <!-- Top Cyber Accent Bar -->
  <path d="M 18 4 L 80 4 L 90 14 L 18 14 Z" fill="{accent}" opacity="0.85"/>
  <text x="24" y="12" fill="#070b19" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace" font-size="7.5" font-weight="900" letter-spacing="1">FEATURED</text>

  <!-- Category & Status Line -->
  <g transform="translate(20, 34)">
    <text x="0" y="0" fill="#94a3b8" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace" font-size="8.5" font-weight="700" letter-spacing="1">{category}</text>
    
    <!-- Status Pill -->
    <rect x="300" y="-10" width="110" height="15" rx="3" fill="#030712" stroke="{status_color}" stroke-width="0.8"/>
    <circle cx="308" cy="-2.5" r="2.5" fill="{status_color}"/>
    <text x="316" y="0" fill="{status_color}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace" font-size="7.5" font-weight="700" letter-spacing="0.5">{status}</text>
  </g>

  <!-- Project Icon & Title Header -->
  <g transform="translate(20, 48)">
    <g transform="translate(0, 0)">
      {icon}
    </g>
    <text x="38" y="21" fill="#ffffff" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="16" font-weight="800" letter-spacing="0.2">{title}</text>
  </g>

  <!-- Project Description (wrapped visually) -->
  <g transform="translate(20, 88)">
    <text x="0" y="14" fill="#cbd5e1" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="11.5" font-weight="400" width="410">
      <tspan x="0" dy="0">{desc_line1}</tspan>
      <tspan x="0" dy="16">{desc_line2}</tspan>
    </text>
  </g>

  <!-- Technology Tags Footer -->
  <g transform="translate(20, 142)">
    {tags_svg}
  </g>

  <!-- Corner Decals -->
  <path d="M 4 25 L 4 4 L 25 4" fill="none" stroke="{accent}" stroke-width="2.5"/>
  <path d="M 446 25 L 446 4 L 425 4" fill="none" stroke="{accent}" stroke-width="2.5"/>
  <path d="M 4 165 L 4 186 L 25 186" fill="none" stroke="{accent}" stroke-width="2.5"/>
  <path d="M 446 165 L 446 186 L 425 186" fill="none" stroke="{accent}" stroke-width="2.5"/>
</svg>"""

out_dir = "/home/moeen/Documents/antigravity/agitated-goodall/assets/cards"
os.makedirs(out_dir, exist_ok=True)

for i, p in enumerate(PROJECTS):
    # split desc into two lines
    words = p["desc"].split()
    half = len(words) // 2
    l1 = " ".join(words[:half+1])
    l2 = " ".join(words[half+1:])

    tags_svg = ""
    offset = 0
    for t in p["tags"]:
        width = len(t) * 7.5 + 16
        tags_svg += f'''
        <g transform="translate({offset}, 0)">
          <rect x="0" y="0" width="{width}" height="20" rx="4" fill="#0f172a" stroke="{p['border']}" stroke-width="0.8"/>
          <text x="{width/2}" y="13.5" text-anchor="middle" fill="{p['accent_glow']}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace" font-size="9" font-weight="700">{t}</text>
        </g>
        '''
        offset += width + 8

    svg = card_template.format(
        id=i,
        title=p["title"],
        category=p["category"],
        desc_line1=l1,
        desc_line2=l2,
        tags_svg=tags_svg,
        accent=p["accent"],
        accent_glow=p["accent_glow"],
        border=p["border"],
        status=p["status"],
        status_color=p["status_color"],
        icon=p["icon"]
    )
    with open(os.path.join(out_dir, p["filename"]), "w") as f:
        f.write(svg)

print(f"Generated {len(PROJECTS)} project cards in {out_dir}")
