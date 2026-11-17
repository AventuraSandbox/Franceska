"""Layout diff of two screenshots with only the standard library (PNG in, PNG out).

Layout mode turns both screenshots into edge maps, so a rebrand's new colours do not count.
"""
import json
import struct
import zlib

WORK_W = 240          # edge maps are computed at this width
CELL = 8              # grid cell size at work scale


class PngError(Exception):
    pass


def read_png(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise PngError(f"{path}: not a PNG file")
    pos, idat, plte = 8, [], None
    w = h = depth = ctype = interlace = None
    while pos + 8 <= len(data):
        ln, typ = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + ln]
        pos += 12 + ln
        if typ == b"IHDR":
            w, h, depth, ctype, _c, _f, interlace = struct.unpack(">IIBBBBB", body)
        elif typ == b"PLTE":
            plte = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
        elif typ == b"IDAT":
            idat.append(body)
        elif typ == b"IEND":
            break
    if w is None or not idat:
        raise PngError(f"{path}: damaged PNG")
    if interlace:
        raise PngError(f"{path}: interlaced PNG. Re-save it without interlacing")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(ctype)
    if channels is None:
        raise PngError(f"{path}: unsupported colour type {ctype}")
    raw = zlib.decompress(b"".join(idat))
    bits_pp = channels * depth
    bpp = max(1, bits_pp // 8)
    stride = (w * bits_pp + 7) // 8
    rows, prev = [], bytearray(stride)
    p = 0
    for _ in range(h):
        ft = raw[p]
        line = bytearray(raw[p + 1:p + 1 + stride])
        p += 1 + stride
        if ft == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif ft == 2:
            line = bytearray((a + b) & 255 for a, b in zip(line, prev))
        elif ft == 3:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 255
        elif ft == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        elif ft != 0:
            raise PngError(f"{path}: bad filter {ft}")
        rows.append(line)
        prev = line
    return w, h, to_gray(rows, w, depth, ctype, channels, plte)


def to_gray(rows, w, depth, ctype, channels, plte):
    out = []
    for line in rows:
        if depth == 8 and ctype == 6:
            g = []
            for x in range(w):
                r, gg, b, a = line[4 * x:4 * x + 4]
                v = 0.299 * r + 0.587 * gg + 0.114 * b
                g.append(int(v * a / 255 + 255 * (1 - a / 255)))
        elif depth == 8 and ctype == 2:
            g = [int(0.299 * line[3 * x] + 0.587 * line[3 * x + 1] + 0.114 * line[3 * x + 2]) for x in range(w)]
        elif depth == 8 and ctype == 0:
            g = list(line[:w])
        elif depth == 8 and ctype == 4:
            g = [int(line[2 * x] * line[2 * x + 1] / 255 + 255 * (1 - line[2 * x + 1] / 255)) for x in range(w)]
        elif depth == 16:
            step = 2 * channels
            g = []
            for x in range(w):
                px = [line[x * step + 2 * k] for k in range(channels)]  # high bytes
                if ctype == 0:
                    g.append(px[0])
                elif ctype == 2:
                    g.append(int(0.299 * px[0] + 0.587 * px[1] + 0.114 * px[2]))
                elif ctype == 4:
                    g.append(int(px[0] * px[1] / 255 + 255 * (1 - px[1] / 255)))
                else:
                    a = px[3]
                    g.append(int((0.299 * px[0] + 0.587 * px[1] + 0.114 * px[2]) * a / 255 + 255 * (1 - a / 255)))
        else:  # sub-byte gray or palette
            vals = []
            mask = (1 << depth) - 1
            for byte in line:
                for shift in range(8 - depth, -1, -depth):
                    vals.append((byte >> shift) & mask)
            vals = vals[:w]
            if ctype == 3:
                pal = plte or [(0, 0, 0)] * (1 << depth)
                g = [int(0.299 * pal[v][0] + 0.587 * pal[v][1] + 0.114 * pal[v][2]) for v in vals]
            else:
                scale = 255 // mask
                g = [v * scale for v in vals]
        out.append(g)
    return out


def resize_gray(gray, w, h, tw):
    th = max(1, round(h * tw / w))
    xs = [int(i * w / tw) for i in range(tw + 1)]
    xs[-1] = w
    cols = []
    for row in gray:
        cols.append([sum(row[xs[i]:xs[i + 1]]) / max(1, xs[i + 1] - xs[i]) for i in range(tw)])
    ys = [int(j * h / th) for j in range(th + 1)]
    ys[-1] = h
    out = []
    for j in range(th):
        a, b = ys[j], max(ys[j] + 1, ys[j + 1])
        n = b - a
        out.append([sum(cols[y][i] for y in range(a, b)) / n for i in range(tw)])
    return out


def edges(gray):
    h, w = len(gray), len(gray[0])
    mag = [[0.0] * w for _ in range(h)]
    allv = []
    for y in range(1, h - 1):
        r0, r1, r2 = gray[y - 1], gray[y], gray[y + 1]
        for x in range(1, w - 1):
            gx = (r0[x + 1] + 2 * r1[x + 1] + r2[x + 1]) - (r0[x - 1] + 2 * r1[x - 1] + r2[x - 1])
            gy = (r2[x - 1] + 2 * r2[x] + r2[x + 1]) - (r0[x - 1] + 2 * r0[x] + r0[x + 1])
            m = abs(gx) + abs(gy)
            mag[y][x] = m
            if m > 0:
                allv.append(m)
    if not allv:
        return [[0] * w for _ in range(h)]
    allv.sort()
    p98 = allv[int(0.98 * (len(allv) - 1))]
    thr = max(24.0, 0.25 * p98)   # relative, so a contrast change does not read as a layout change
    return [[1 if v >= thr else 0 for v in row] for row in mag]


def cell_density(edge):
    h, w = len(edge), len(edge[0])
    gh, gw = (h + CELL - 1) // CELL, (w + CELL - 1) // CELL
    grid = [[0.0] * gw for _ in range(gh)]
    for cy in range(gh):
        for cx in range(gw):
            tot = cnt = 0
            for y in range(cy * CELL, min(h, (cy + 1) * CELL)):
                seg = edge[y][cx * CELL:(cx + 1) * CELL]
                tot += sum(seg)
                cnt += len(seg)
            grid[cy][cx] = tot / cnt if cnt else 0.0
    return grid


def sim(a, b):
    m = max(a, b)
    return 1.0 if m == 0 else 1 - abs(a - b) / m


def compare_grids(ga, gb):
    gh, gw = min(len(ga), len(gb)), len(ga[0])
    total = wsum = 0.0
    bad = {}
    for cy in range(gh):
        for cx in range(gw):
            a, b = ga[cy][cx], gb[cy][cx]
            weight = max(a, b)
            if weight < 0.04:
                continue
            best_ab = best_ba = 0.0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    y, x = cy + dy, cx + dx
                    if 0 <= y < gh and 0 <= x < gw:
                        best_ab = max(best_ab, sim(a, gb[y][x]))
                        best_ba = max(best_ba, sim(ga[y][x], b))
            s = (best_ab + best_ba) / 2
            total += s * weight
            wsum += weight
            if s < 0.5:
                bad[(cy, cx)] = weight
    return (100.0 * total / wsum if wsum else 100.0), bad


def regions(bad, scale_x, scale_y):
    seen, out = set(), []
    for start in bad:
        if start in seen:
            continue
        stack, comp = [start], []
        seen.add(start)
        while stack:
            cy, cx = stack.pop()
            comp.append((cy, cx))
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (cy + d[0], cx + d[1])
                if n in bad and n not in seen:
                    seen.add(n)
                    stack.append(n)
        ys = [c[0] for c in comp]
        xs = [c[1] for c in comp]
        out.append({
            "x": int(min(xs) * CELL * scale_x), "y": int(min(ys) * CELL * scale_y),
            "w": int((max(xs) - min(xs) + 1) * CELL * scale_x),
            "h": int((max(ys) - min(ys) + 1) * CELL * scale_y),
            "weight": round(sum(bad[c] for c in comp), 2),
        })
    out.sort(key=lambda r: -r["weight"])
    return out[:8]


def write_png(path, w, h, rows):
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)


def diff_image(path, ea, eb, factor=3):
    h = max(len(ea), len(eb))
    w = len(ea[0])
    rows = []
    for y in range(h):
        row = []
        for x in range(w):
            a = ea[y][x] if y < len(ea) else 0
            b = eb[y][x] if y < len(eb) else 0
            px = (255, 255, 255)
            if a and b:
                px = (150, 150, 150)
            elif a:
                px = (220, 40, 40)      # only in the original
            elif b:
                px = (40, 90, 220)      # only in your app
            row.extend(px * factor)
        for _ in range(factor):
            rows.append(row)
    write_png(path, w * factor, h * factor, rows)


def label(score):
    return "matches" if score >= 90 else "close" if score >= 75 else "partly" if score >= 50 else "different"


def compare(path_a, path_b, mode="layout", out=None):
    wa, ha, ga = read_png(path_a)
    wb, hb, gb = read_png(path_b)
    ratio_a, ratio_b = ha / wa, hb / wb
    result = {"mode": mode, "original_size": [wa, ha], "clone_size": [wb, hb]}
    if abs(ratio_a - ratio_b) / max(ratio_a, ratio_b) > 0.15:
        result["height_note"] = (f"your page is {'longer' if ratio_b > ratio_a else 'shorter'} "
                                 f"({ratio_b / ratio_a:.2f}x the original's height at the same width)")
    if mode == "pixel":
        tw = min(WORK_W * 3, wa, wb)
        A, B = resize_gray(ga, wa, ha, tw), resize_gray(gb, wb, hb, tw)
        h = min(len(A), len(B))
        same = sum(1 for y in range(h) for x in range(tw) if abs(A[y][x] - B[y][x]) <= 16)
        score = 100.0 * same / (h * tw)
        result.update(score=round(score, 1), label=label(score), regions=[])
        if out:
            diff_image(out, [[1 if abs(A[y][x] - B[y][x]) > 16 else 0 for x in range(tw)] for y in range(h)],
                       [[0] * tw for _ in range(h)], factor=1)
        return result
    ea = edges(resize_gray(ga, wa, ha, WORK_W))
    eb = edges(resize_gray(gb, wb, hb, WORK_W))
    score, bad = compare_grids(cell_density(ea), cell_density(eb))
    result.update(score=round(score, 1), label=label(score),
                  regions=regions(bad, wa / WORK_W, ha / len(ea)))
    if out:
        diff_image(out, ea, eb)
    return result


def run(args):
    try:
        res = compare(args.original, args.yours, args.mode, args.out)
    except PngError as exc:
        raise SystemExit(f"error: {exc}")
    if args.json:
        print(json.dumps(res, indent=2))
        return 0
    print(f"layout score {res['score']} ({res['label']}), mode {res['mode']}")
    if "height_note" in res:
        print("note: " + res["height_note"])
    for r in res["regions"][:5]:
        print(f"  differs: x={r['x']} y={r['y']} w={r['w']} h={r['h']} (in the original's pixels)")
    if args.out:
        print(f"diff image: {args.out}  (red = only in original, blue = only in yours, grey = both)")
    return 0
