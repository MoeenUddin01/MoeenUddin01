#!/usr/bin/env python3
import os

BADGES = [
    {
        "filename": "python.svg",
        "name": "Python 3.12",
        "color": "#00F0FF",
        "border": "#00F0FF",
        "bg_accent": "#0284c7",
        "icon": '<path d="M14 4h8a8 8 0 0 1 8 8v4h-8a2 2 0 0 0-2 2v2H10a8 8 0 0 1-8-8v-4a4 4 0 0 1 4-4h8zm2 3a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm10 25h-8a8 8 0 0 1-8-8v-4h8a2 2 0 0 0 2-2v-2h10a8 8 0 0 1 8 8v4a4 4 0 0 1-4 4h-8zm-2-3a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z" fill="#00F0FF"/>'
    },
    {
        "filename": "pytorch.svg",
        "name": "PyTorch",
        "color": "#FF6B6B",
        "border": "#EE4C2C",
        "bg_accent": "#be123c",
        "icon": '<path d="M21 5a11 11 0 0 1 4 21.3l-2.4-2.4a8 8 0 0 0-3.3-15.4V5zm-2 2.5v3.6a8 8 0 0 0-3.3 15.4L13.3 29A11 11 0 0 1 19 7.5zM22 3l2 2-2 2-2-2 2-2z" fill="#FF6B6B"/>'
    },
    {
        "filename": "langgraph.svg",
        "name": "LangGraph",
        "color": "#C084FC",
        "border": "#A855F7",
        "bg_accent": "#7e22ce",
        "icon": '<circle cx="10" cy="18" r="4" fill="#C084FC"/><circle cx="26" cy="10" r="4" fill="#A855F7"/><circle cx="26" cy="26" r="4" fill="#38BDF8"/><path d="M13 16l10-4M13 20l10 4" stroke="#C084FC" stroke-width="2"/>'
    },
    {
        "filename": "langchain.svg",
        "name": "LangChain",
        "color": "#38BDF8",
        "border": "#0284C7",
        "bg_accent": "#0369a1",
        "icon": '<rect x="6" y="10" width="10" height="16" rx="5" fill="none" stroke="#38BDF8" stroke-width="2"/><rect x="20" y="10" width="10" height="16" rx="5" fill="none" stroke="#38BDF8" stroke-width="2"/><path d="M16 18h4" stroke="#38BDF8" stroke-width="2.5"/>'
    },
    {
        "filename": "fastapi.svg",
        "name": "FastAPI",
        "color": "#00F0FF",
        "border": "#059669",
        "bg_accent": "#047857",
        "icon": '<circle cx="18" cy="18" r="12" fill="none" stroke="#00F0FF" stroke-width="2"/><path d="M19 8l-6 11h5l-2 9 8-12h-5z" fill="#00F0FF"/>'
    },
    {
        "filename": "docker.svg",
        "name": "Docker",
        "color": "#38BDF8",
        "border": "#2563EB",
        "bg_accent": "#1d4ed8",
        "icon": '<rect x="6" y="14" width="4" height="4" fill="#38BDF8"/><rect x="11" y="14" width="4" height="4" fill="#38BDF8"/><rect x="16" y="14" width="4" height="4" fill="#38BDF8"/><rect x="11" y="9" width="4" height="4" fill="#38BDF8"/><rect x="16" y="9" width="4" height="4" fill="#38BDF8"/><rect x="21" y="14" width="4" height="4" fill="#38BDF8"/><path d="M4 19c1 5 7 8 16 8 8 0 10-3 12-6-1 0-3-1-3-3 0 0-4-1-6 2-4 0-8-1-11-2-3-1-6 0-8 1z" fill="#38BDF8"/>'
    },
    {
        "filename": "mcp.svg",
        "name": "MCP Architecture",
        "color": "#A855F7",
        "border": "#9333EA",
        "bg_accent": "#6b21a8",
        "icon": '<rect x="8" y="8" width="20" height="20" rx="4" fill="none" stroke="#A855F7" stroke-width="2"/><circle cx="14" cy="14" r="2" fill="#A855F7"/><circle cx="22" cy="14" r="2" fill="#A855F7"/><circle cx="18" cy="22" r="2.5" fill="#38BDF8"/><path d="M14 16l4 4 4-4" stroke="#A855F7" stroke-width="1.5" fill="none"/>'
    },
    {
        "filename": "rag.svg",
        "name": "Spec-Driven RAG",
        "color": "#34D399",
        "border": "#059669",
        "bg_accent": "#065f46",
        "icon": '<path d="M8 8h12a4 4 0 0 1 4 4v14H8a2 2 0 0 1-2-2V10a2 2 0 0 1 2-2z" fill="none" stroke="#34D399" stroke-width="2"/><circle cx="22" cy="20" r="5" fill="none" stroke="#34D399" stroke-width="2"/><path d="M26 24l4 4" stroke="#34D399" stroke-width="2"/>'
    },
    {
        "filename": "robotics.svg",
        "name": "PyBullet / Robotics",
        "color": "#FBBF24",
        "border": "#D97706",
        "bg_accent": "#b45309",
        "icon": '<rect x="10" y="10" width="16" height="14" rx="3" fill="none" stroke="#FBBF24" stroke-width="2"/><circle cx="14" cy="16" r="2" fill="#FBBF24"/><circle cx="22" cy="16" r="2" fill="#FBBF24"/><path d="M15 21h6M18 6v4M7 16h3M26 16h3" stroke="#FBBF24" stroke-width="2"/>'
    },
    {
        "filename": "typescript.svg",
        "name": "TypeScript",
        "color": "#38BDF8",
        "border": "#3178C6",
        "bg_accent": "#1e40af",
        "icon": '<rect x="6" y="6" width="24" height="24" rx="4" fill="none" stroke="#38BDF8" stroke-width="2"/><path d="M12 14h6M15 14v10M20 22c1 1 3 2 5 1 2-1 2-3 0-4-2-1-3-2-3-3 0-2 2-3 4-2M25 15v1" stroke="#38BDF8" stroke-width="1.8" fill="none"/>'
    },
    {
        "filename": "linux.svg",
        "name": "Linux / Bash",
        "color": "#FDE047",
        "border": "#EAB308",
        "bg_accent": "#854d0e",
        "icon": '<path d="M12 12l6 6-6 6M20 24h6" stroke="#FDE047" stroke-width="2.5" stroke-linecap="round"/>'
    },
    {
        "filename": "postgresql.svg",
        "name": "PostgreSQL",
        "color": "#60A5FA",
        "border": "#336791",
        "bg_accent": "#1e3a8a",
        "icon": '<path d="M18 6c-6 0-11 4-11 9 0 3 2 6 5 7v4l4-3c1 0 1 1 2 1 6 0 11-4 11-9s-5-9-11-9z" fill="none" stroke="#60A5FA" stroke-width="2"/><circle cx="14" cy="14" r="1.5" fill="#60A5FA"/>'
    }
]

template = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 40" width="180" height="40">
  <defs>
    <linearGradient id="bg_{id}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#070b19"/>
      <stop offset="60%" stop-color="#0b112c"/>
      <stop offset="100%" stop-color="{bg_accent}" stop-opacity="0.3"/>
    </linearGradient>
    <filter id="glow_{id}" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="2.5" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>
  <rect x="2" y="2" width="176" height="36" rx="8" fill="url(#bg_{id})" stroke="{border}" stroke-width="1.2" filter="url(#glow_{id})"/>
  <g transform="translate(6, 2)">
    {icon}
  </g>
  <text x="44" y="24" fill="{color}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="11.5" font-weight="700" letter-spacing="0.5">{name}</text>
  <circle cx="166" cy="20" r="2.5" fill="{color}" opacity="0.8"/>
</svg>"""

out_dir = "/home/moeen/Documents/antigravity/agitated-goodall/assets/icons"
os.makedirs(out_dir, exist_ok=True)

for i, b in enumerate(BADGES):
    svg_content = template.format(
        id=i,
        name=b["name"],
        color=b["color"],
        border=b["border"],
        bg_accent=b["bg_accent"],
        icon=b["icon"]
    )
    with open(os.path.join(out_dir, b["filename"]), "w") as f:
        f.write(svg_content)

print(f"Generated {len(BADGES)} badges in {out_dir}")
