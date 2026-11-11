#!/usr/bin/env python3
"""生成 PWA 图标：蓝色圆角底 + 白色行李箱图案，纯标准库实现（超采样抗锯齿）。"""
import struct, zlib, os

BG = (0, 113, 227)      # #0071e3
FG = (255, 255, 255)

def in_rounded_rect(x, y, cx, cy, hw, hh, r):
    dx = abs(x - cx) - (hw - r)
    dy = abs(y - cy) - (hh - r)
    if dx <= 0 or dy <= 0:
        return abs(x - cx) <= hw and abs(y - cy) <= hh
    return dx * dx + dy * dy <= r * r

def draw(size, maskable=False):
    S = 4  # 超采样倍数
    N = size * S
    # maskable 图标：图案缩小到安全区（中心 80%）
    scale = 0.72 if maskable else 1.0
    margin = size * (0.14 if maskable else 0.10)  # 背景圆角边距
    radius = size * (0.20 if not maskable else 0.0)  # maskable 用满底，避免裁切
    cx = cy = N / 2

    def fg_at(x, y):
        # 坐标归一化到 0..size 的“图案空间”
        u = x / S
        v = y / S
        pcx = pcy = size / 2
        # 行李箱主体
        bw = size * 0.30 * scale   # 半宽
        bh = size * 0.22 * scale   # 半高
        body_cy = pcy + size * 0.05 * scale
        if in_rounded_rect(u, v, pcx, body_cy, bw, bh, size * 0.045 * scale):
            # 箱体上的两条束带（蓝色镂空）
            strap_w = size * 0.035 * scale
            for sx in (pcx - size * 0.14 * scale, pcx + size * 0.14 * scale):
                if in_rounded_rect(u, v, sx, body_cy, strap_w, bh, strap_w):
                    return False
            return True
        # 拉杆（提手）：顶部横条 + 两侧竖条
        handle_w = size * 0.13 * scale
        handle_h = size * 0.035 * scale
        if in_rounded_rect(u, v, pcx, pcy - size * 0.24 * scale, handle_w, handle_h, handle_h):
            return True
        leg_w = size * 0.028 * scale
        leg_top = pcy - size * 0.24 * scale
        leg_bot = body_cy - bh
        for lx in (pcx - handle_w, pcx + handle_w):
            if in_rounded_rect(u, v, lx, (leg_top + leg_bot) / 2, leg_w, (leg_bot - leg_top) / 2, leg_w):
                return True
        return False

    px = bytearray()
    for y in range(N):
        px.append(0)  # filter type 0
        row = bytearray()
        for x in range(N):
            # 背景
            if radius > 0:
                bg_on = in_rounded_rect(x, y, cx, cy, N / 2 - margin * S / 2, N / 2 - margin * S / 2, radius * S)
            else:
                bg_on = True
            fg_on = fg_at(x, y) if bg_on else False
            if fg_on:
                row += bytes(FG) + b"\xff"
            elif bg_on:
                row += bytes(BG) + b"\xff"
            else:
                row += b"\x00\x00\x00\x00"
        px += row

    # 下采样：S x S 平均
    out = bytearray()
    for y in range(size):
        out.append(0)
        for x in range(size):
            r = g = b = a = 0
            for sy in range(S):
                base = (y * S + sy) * (1 + N * 4) + 1 + x * S * 4
                for sx in range(S):
                    i = base + sx * 4
                    r += px[i]; g += px[i + 1]; b += px[i + 2]; a += px[i + 3]
            n = S * S
            out += bytes((r // n, g // n, b // n, a // n))

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(out), 9)) + chunk(b"IEND", b""))

here = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(here, "icons"), exist_ok=True)
for size in (192, 512):
    for maskable in (False, True):
        name = f"icon{'-maskable' if maskable else ''}-{size}.png"
        with open(os.path.join(here, "icons", name), "wb") as f:
            f.write(draw(size, maskable))
        print("written", name)
