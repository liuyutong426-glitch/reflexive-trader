"""生成 PWA 配置的 HTML 片段（带 base64 图标）"""
import base64

def get_icon_base64(filename):
    with open(filename, "rb") as f:
        return base64.b64encode(f.read()).decode()

# 读取 Apple icon
apple_icon_180 = get_icon_base64("apple-touch-icon.png")

# 生成 HTML
PWA_HTML = f"""
<link rel="manifest" href="./manifest.json">
<meta name="theme-color" content="#00bcd4">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="ReflexiveTrader">
<link rel="apple-touch-icon" href="data:image/png;base64,{apple_icon_180}">
<link rel="icon" type="image/png" sizes="192x192" href="./icon-192.png">
<link rel="shortcut icon" href="./favicon.ico">
"""

if __name__ == "__main__":
    print(PWA_HTML[:500])
    print(f"\n... (total length: {len(PWA_HTML)} chars)")
