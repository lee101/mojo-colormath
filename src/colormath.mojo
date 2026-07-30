"""Numerical color conversion and color-difference kernels."""

from std.math import atan2, cbrt, cos, exp, sin, sqrt
from std.sys.info import simd_width_of

comptime Ptr = UnsafePointer[Float64, AnyOrigin[mut=True]]
comptime PI = 3.1415926535897932384626433832795
comptime DEG = 180.0 / PI
comptime RAD = PI / 180.0
comptime CIE_E = 216.0 / 24389.0
comptime CIE_K = 24389.0 / 27.0


def p(addr: Int) -> Ptr:
    return Ptr(unsafe_from_address=addr)


def sq(x: Float64) -> Float64:
    return x * x


def pow7(x: Float64) -> Float64:
    var x2 = x * x
    var x4 = x2 * x2
    return x4 * x2 * x


def pow7_simd[W: Int](
    x: SIMD[DType.float64, W]
) -> SIMD[DType.float64, W]:
    var x2 = x * x
    var x4 = x2 * x2
    return x4 * x2 * x


def hue_degrees(y: Float64, x: Float64) -> Float64:
    var h = atan2(y, x) * DEG
    if h < 0.0:
        h += 360.0
    return h


def cie2000_one(
    l1: Float64,
    a1: Float64,
    b1: Float64,
    c1: Float64,
    l2: Float64,
    a2: Float64,
    b2: Float64,
    kl: Float64,
    kc: Float64,
    kh: Float64,
) -> Float64:
    var c2 = sqrt(a2 * a2 + b2 * b2)
    var avg_l = (l1 + l2) * 0.5
    var avg_c = (c1 + c2) * 0.5
    var avg_c7 = pow7(avg_c)
    var p25 = pow7(25.0)
    var g = 0.5 * (1.0 - sqrt(avg_c7 / (avg_c7 + p25)))
    var a1p = (1.0 + g) * a1
    var a2p = (1.0 + g) * a2
    var c1p = sqrt(a1p * a1p + b1 * b1)
    var c2p = sqrt(a2p * a2p + b2 * b2)
    var avg_cp = (c1p + c2p) * 0.5
    var h1p = hue_degrees(b1, a1p)
    var h2p = hue_degrees(b2, a2p)
    var hdiff = h2p - h1p
    var avg_hp = (h1p + h2p) * 0.5
    if abs(h1p - h2p) > 180.0:
        avg_hp += 180.0
    var t = (
        1.0
        - 0.17 * cos((avg_hp - 30.0) * RAD)
        + 0.24 * cos(2.0 * avg_hp * RAD)
        + 0.32 * cos((3.0 * avg_hp + 6.0) * RAD)
        - 0.20 * cos((4.0 * avg_hp - 63.0) * RAD)
    )
    var delta_hp = hdiff
    if abs(hdiff) > 180.0:
        if h2p > h1p:
            delta_hp -= 360.0
        else:
            delta_hp += 360.0
    var dlp = l2 - l1
    var dcp = c2p - c1p
    var dhp = 2.0 * sqrt(c1p * c2p) * sin(delta_hp * RAD * 0.5)
    var lterm = avg_l - 50.0
    var sl = 1.0 + 0.015 * lterm * lterm / sqrt(20.0 + lterm * lterm)
    var sc = 1.0 + 0.045 * avg_cp
    var sh = 1.0 + 0.015 * avg_cp * t
    var dro_arg = (avg_hp - 275.0) / 25.0
    var delta_ro = 30.0 * exp(-(dro_arg * dro_arg))
    var avg_cp7 = pow7(avg_cp)
    var rc = sqrt(avg_cp7 / (avg_cp7 + p25))
    var rt = -2.0 * rc * sin(2.0 * delta_ro * RAD)
    var vl = dlp / (sl * kl)
    var vc = dcp / (sc * kc)
    var vh = dhp / (sh * kh)
    return sqrt(max(0.0, vl * vl + vc * vc + vh * vh + rt * vc * vh))


def cie2000_range(
    samples: Ptr,
    dst: Ptr,
    start: Int,
    end: Int,
    l1: Float64,
    a1: Float64,
    b1: Float64,
    c1: Float64,
    kl: Float64,
    kc: Float64,
    kh: Float64,
):
    comptime W = simd_width_of[DType.float64]()
    var i = start
    var vector_end = end - (end - start) % W
    var p25 = pow7(25.0)
    var b1v = SIMD[DType.float64, W](b1)
    while i < vector_end:
        var j = 3 * i
        var l2 = (samples + j).strided_load[width=W](3)
        var a2 = (samples + j + 1).strided_load[width=W](3)
        var b2 = (samples + j + 2).strided_load[width=W](3)
        var c2 = sqrt(a2 * a2 + b2 * b2)
        var avg_l = (l1 + l2) * 0.5
        var avg_c = (c1 + c2) * 0.5
        var avg_c7 = pow7_simd(avg_c)
        var g = 0.5 * (1.0 - sqrt(avg_c7 / (avg_c7 + p25)))
        var a1p = (1.0 + g) * a1
        var a2p = (1.0 + g) * a2
        var c1p = sqrt(a1p * a1p + b1 * b1)
        var c2p = sqrt(a2p * a2p + b2 * b2)
        var avg_cp = (c1p + c2p) * 0.5
        var h1p = atan2(b1v, a1p) * DEG
        var h2p = atan2(b2, a2p) * DEG
        h1p = h1p.lt(0.0).select(h1p + 360.0, h1p)
        h2p = h2p.lt(0.0).select(h2p + 360.0, h2p)
        var hdiff = h2p - h1p
        var wide = abs(hdiff).gt(180.0)
        var avg_hp = (h1p + h2p) * 0.5 + wide.select(180.0, 0.0)
        var t = (
            1.0
            - 0.17 * cos((avg_hp - 30.0) * RAD)
            + 0.24 * cos(2.0 * avg_hp * RAD)
            + 0.32 * cos((3.0 * avg_hp + 6.0) * RAD)
            - 0.20 * cos((4.0 * avg_hp - 63.0) * RAD)
        )
        var adjustment = h2p.gt(h1p).select(-360.0, 360.0)
        var delta_hp = wide.select(hdiff + adjustment, hdiff)
        var dlp = l2 - l1
        var dcp = c2p - c1p
        var dhp = 2.0 * sqrt(c1p * c2p) * sin(delta_hp * RAD * 0.5)
        var lterm = avg_l - 50.0
        var sl = 1.0 + 0.015 * lterm * lterm / sqrt(20.0 + lterm * lterm)
        var sc = 1.0 + 0.045 * avg_cp
        var sh = 1.0 + 0.015 * avg_cp * t
        var dro_arg = (avg_hp - 275.0) / 25.0
        var delta_ro = 30.0 * exp(-(dro_arg * dro_arg))
        var avg_cp7 = pow7_simd(avg_cp)
        var rc = sqrt(avg_cp7 / (avg_cp7 + p25))
        var rt = -2.0 * rc * sin(2.0 * delta_ro * RAD)
        var vl = dlp / (sl * kl)
        var vc = dcp / (sc * kc)
        var vh = dhp / (sh * kh)
        var distance2 = vl * vl + vc * vc + vh * vh + rt * vc * vh
        dst.store(
            i, sqrt(max(distance2, SIMD[DType.float64, W](0.0)))
        )
        i += W
    while i < end:
        var j = 3 * i
        dst[i] = cie2000_one(
            l1,
            a1,
            b1,
            c1,
            samples[j],
            samples[j + 1],
            samples[j + 2],
            kl,
            kc,
            kh,
        )
        i += 1


@export("mcm_delta_e_cie1976")
def mcm_delta_e_cie1976(
    ref_addr: Int, samples_addr: Int, dst_addr: Int, n: Int
) abi("C") -> Int32:
    if n < 0 or (n > 0 and (ref_addr == 0 or samples_addr == 0 or dst_addr == 0)):
        return 1
    if n == 0:
        return 0
    var refp = p(ref_addr)
    var samples = p(samples_addr)
    var dst = p(dst_addr)
    for i in range(n):
        var j = 3 * i
        var dl = refp[0] - samples[j]
        var da = refp[1] - samples[j + 1]
        var db = refp[2] - samples[j + 2]
        dst[i] = sqrt(dl * dl + da * da + db * db)
    return 0


@export("mcm_delta_e_cie1994")
def mcm_delta_e_cie1994(
    ref_addr: Int,
    samples_addr: Int,
    dst_addr: Int,
    n: Int,
    kl: Float64,
    kc: Float64,
    kh: Float64,
    k1: Float64,
    k2: Float64,
) abi("C") -> Int32:
    if n < 0 or (n > 0 and (ref_addr == 0 or samples_addr == 0 or dst_addr == 0)):
        return 1
    if n == 0:
        return 0
    var refp = p(ref_addr)
    var samples = p(samples_addr)
    var dst = p(dst_addr)
    var c1 = sqrt(refp[1] * refp[1] + refp[2] * refp[2])
    var sc = 1.0 + k1 * c1
    var sh = 1.0 + k2 * c1
    for i in range(n):
        var j = 3 * i
        var dl = refp[0] - samples[j]
        var da = refp[1] - samples[j + 1]
        var db = refp[2] - samples[j + 2]
        var c2 = sqrt(samples[j + 1] * samples[j + 1] + samples[j + 2] * samples[j + 2])
        var dc = c1 - c2
        var dh2 = da * da + db * db - dc * dc
        var dh = sqrt(max(0.0, dh2))
        dst[i] = sqrt(sq(dl / kl) + sq(dc / (kc * sc)) + sq(dh / (kh * sh)))
    return 0


@export("mcm_delta_e_cmc")
def mcm_delta_e_cmc(
    ref_addr: Int,
    samples_addr: Int,
    dst_addr: Int,
    n: Int,
    pl: Float64,
    pc: Float64,
) abi("C") -> Int32:
    if n < 0 or (n > 0 and (ref_addr == 0 or samples_addr == 0 or dst_addr == 0)):
        return 1
    if n == 0:
        return 0
    var refp = p(ref_addr)
    var samples = p(samples_addr)
    var dst = p(dst_addr)
    var l1 = refp[0]
    var c1 = sqrt(refp[1] * refp[1] + refp[2] * refp[2])
    var h1 = hue_degrees(refp[2], refp[1])
    var c14 = sq(sq(c1))
    var f = sqrt(c14 / (c14 + 1900.0))
    var t: Float64
    if h1 >= 164.0 and h1 <= 345.0:
        t = 0.56 + abs(0.2 * cos((h1 + 168.0) * RAD))
    else:
        t = 0.36 + abs(0.4 * cos((h1 + 35.0) * RAD))
    var sl: Float64
    if l1 < 16.0:
        sl = 0.511
    else:
        sl = (0.040975 * l1) / (1.0 + 0.01765 * l1)
    var sc = (0.0638 * c1) / (1.0 + 0.0131 * c1) + 0.638
    var sh = sc * (f * t + 1.0 - f)
    for i in range(n):
        var j = 3 * i
        var dl = refp[0] - samples[j]
        var da = refp[1] - samples[j + 1]
        var db = refp[2] - samples[j + 2]
        var c2 = sqrt(samples[j + 1] * samples[j + 1] + samples[j + 2] * samples[j + 2])
        var dc = c1 - c2
        var dh = sqrt(max(0.0, da * da + db * db - dc * dc))
        dst[i] = sqrt(sq(dl / (pl * sl)) + sq(dc / (pc * sc)) + sq(dh / sh))
    return 0


@export("mcm_delta_e_cie2000")
def mcm_delta_e_cie2000(
    ref_addr: Int,
    samples_addr: Int,
    dst_addr: Int,
    n: Int,
    kl: Float64,
    kc: Float64,
    kh: Float64,
) abi("C") -> Int32:
    if n < 0 or (n > 0 and (ref_addr == 0 or samples_addr == 0 or dst_addr == 0)):
        return 1
    if n == 0:
        return 0
    var refp = p(ref_addr)
    var samples = p(samples_addr)
    var dst = p(dst_addr)
    var l1 = refp[0]
    var a1 = refp[1]
    var b1 = refp[2]
    var c1 = sqrt(a1 * a1 + b1 * b1)
    cie2000_range(samples, dst, 0, n, l1, a1, b1, c1, kl, kc, kh)
    return 0


@export("mcm_lab_to_xyz")
def mcm_lab_to_xyz(
    src_addr: Int, dst_addr: Int, n: Int, wx: Float64, wy: Float64, wz: Float64
) abi("C") -> Int32:
    if n < 0 or (n > 0 and (src_addr == 0 or dst_addr == 0)):
        return 1
    if n == 0:
        return 0
    var src = p(src_addr)
    var dst = p(dst_addr)
    for i in range(n):
        var j = 3 * i
        var y = (src[j] + 16.0) / 116.0
        var x = src[j + 1] / 500.0 + y
        var z = y - src[j + 2] / 200.0
        var x3 = x * x * x
        var y3 = y * y * y
        var z3 = z * z * z
        x = x3 if x3 > CIE_E else (x - 16.0 / 116.0) / 7.787
        y = y3 if y3 > CIE_E else (y - 16.0 / 116.0) / 7.787
        z = z3 if z3 > CIE_E else (z - 16.0 / 116.0) / 7.787
        dst[j] = wx * x
        dst[j + 1] = wy * y
        dst[j + 2] = wz * z
    return 0


def lab_f(t: Float64) -> Float64:
    if t > CIE_E:
        return cbrt(t)
    return 7.787 * t + 16.0 / 116.0


@export("mcm_xyz_to_lab")
def mcm_xyz_to_lab(
    src_addr: Int, dst_addr: Int, n: Int, wx: Float64, wy: Float64, wz: Float64
) abi("C") -> Int32:
    if n < 0 or (n > 0 and (src_addr == 0 or dst_addr == 0)):
        return 1
    if n == 0:
        return 0
    var src = p(src_addr)
    var dst = p(dst_addr)
    for i in range(n):
        var j = 3 * i
        var x = lab_f(src[j] / wx)
        var y = lab_f(src[j + 1] / wy)
        var z = lab_f(src[j + 2] / wz)
        dst[j] = 116.0 * y - 16.0
        dst[j + 1] = 500.0 * (x - y)
        dst[j + 2] = 200.0 * (y - z)
    return 0


@export("mcm_xyz_to_luv")
def mcm_xyz_to_luv(
    src_addr: Int, dst_addr: Int, n: Int, wx: Float64, wy: Float64, wz: Float64
) abi("C") -> Int32:
    if n < 0 or (n > 0 and (src_addr == 0 or dst_addr == 0)):
        return 1
    if n == 0:
        return 0
    var src = p(src_addr)
    var dst = p(dst_addr)
    var wden = wx + 15.0 * wy + 3.0 * wz
    var un = 4.0 * wx / wden
    var vn = 9.0 * wy / wden
    for i in range(n):
        var j = 3 * i
        var x = src[j]
        var y = src[j + 1]
        var z = src[j + 2]
        var den = x + 15.0 * y + 3.0 * z
        var up = 0.0
        var vp = 0.0
        if den != 0.0:
            up = 4.0 * x / den
            vp = 9.0 * y / den
        var fy = lab_f(y / wy)
        var l = 116.0 * fy - 16.0
        dst[j] = l
        dst[j + 1] = 13.0 * l * (up - un)
        dst[j + 2] = 13.0 * l * (vp - vn)
    return 0


@export("mcm_luv_to_xyz")
def mcm_luv_to_xyz(
    src_addr: Int, dst_addr: Int, n: Int, wx: Float64, wy: Float64, wz: Float64
) abi("C") -> Int32:
    if n < 0 or (n > 0 and (src_addr == 0 or dst_addr == 0)):
        return 1
    if n == 0:
        return 0
    var src = p(src_addr)
    var dst = p(dst_addr)
    var wden = wx + 15.0 * wy + 3.0 * wz
    var un = 4.0 * wx / wden
    var vn = 9.0 * wy / wden
    for i in range(n):
        var j = 3 * i
        var l = src[j]
        if l <= 0.0:
            dst[j] = 0.0
            dst[j + 1] = 0.0
            dst[j + 2] = 0.0
        else:
            var up = src[j + 1] / (13.0 * l) + un
            var vp = src[j + 2] / (13.0 * l) + vn
            var y: Float64
            if l > CIE_K * CIE_E:
                var q = (l + 16.0) / 116.0
                y = q * q * q
            else:
                y = l / CIE_K
            dst[j] = y * 9.0 * up / (4.0 * vp)
            dst[j + 1] = y
            dst[j + 2] = y * (12.0 - 3.0 * up - 20.0 * vp) / (4.0 * vp)
    return 0


@export("mcm_cart_to_lch")
def mcm_cart_to_lch(src_addr: Int, dst_addr: Int, n: Int) abi("C") -> Int32:
    if n < 0 or (n > 0 and (src_addr == 0 or dst_addr == 0)):
        return 1
    if n == 0:
        return 0
    var src = p(src_addr)
    var dst = p(dst_addr)
    for i in range(n):
        var j = 3 * i
        dst[j] = src[j]
        dst[j + 1] = sqrt(src[j + 1] * src[j + 1] + src[j + 2] * src[j + 2])
        dst[j + 2] = hue_degrees(src[j + 2], src[j + 1])
    return 0


@export("mcm_lch_to_cart")
def mcm_lch_to_cart(src_addr: Int, dst_addr: Int, n: Int) abi("C") -> Int32:
    if n < 0 or (n > 0 and (src_addr == 0 or dst_addr == 0)):
        return 1
    if n == 0:
        return 0
    var src = p(src_addr)
    var dst = p(dst_addr)
    for i in range(n):
        var j = 3 * i
        var h = src[j + 2] * RAD
        dst[j] = src[j]
        dst[j + 1] = cos(h) * src[j + 1]
        dst[j + 2] = sin(h) * src[j + 1]
    return 0


@export("mcm_xyz_to_xyy")
def mcm_xyz_to_xyy(src_addr: Int, dst_addr: Int, n: Int) abi("C") -> Int32:
    if n < 0 or (n > 0 and (src_addr == 0 or dst_addr == 0)):
        return 1
    if n == 0:
        return 0
    var src = p(src_addr)
    var dst = p(dst_addr)
    for i in range(n):
        var j = 3 * i
        var total = src[j] + src[j + 1] + src[j + 2]
        if total == 0.0:
            dst[j] = 0.0
            dst[j + 1] = 0.0
        else:
            dst[j] = src[j] / total
            dst[j + 1] = src[j + 1] / total
        dst[j + 2] = src[j + 1]
    return 0


@export("mcm_xyy_to_xyz")
def mcm_xyy_to_xyz(src_addr: Int, dst_addr: Int, n: Int) abi("C") -> Int32:
    if n < 0 or (n > 0 and (src_addr == 0 or dst_addr == 0)):
        return 1
    if n == 0:
        return 0
    var src = p(src_addr)
    var dst = p(dst_addr)
    for i in range(n):
        var j = 3 * i
        if src[j + 1] == 0.0:
            dst[j] = 0.0
            dst[j + 1] = 0.0
            dst[j + 2] = 0.0
        else:
            dst[j] = src[j] * src[j + 2] / src[j + 1]
            dst[j + 1] = src[j + 2]
            dst[j + 2] = (1.0 - src[j] - src[j + 1]) * src[j + 2] / src[j + 1]
    return 0


@export("mcm_srgb_to_xyz")
def mcm_srgb_to_xyz(src_addr: Int, dst_addr: Int, n: Int) abi("C") -> Int32:
    if n < 0 or (n > 0 and (src_addr == 0 or dst_addr == 0)):
        return 1
    if n == 0:
        return 0
    var src = p(src_addr)
    var dst = p(dst_addr)
    for i in range(n):
        var j = 3 * i
        var r = src[j]
        var g = src[j + 1]
        var b = src[j + 2]
        r = r / 12.92 if r <= 0.04045 else ((r + 0.055) / 1.055) ** 2.4
        g = g / 12.92 if g <= 0.04045 else ((g + 0.055) / 1.055) ** 2.4
        b = b / 12.92 if b <= 0.04045 else ((b + 0.055) / 1.055) ** 2.4
        dst[j] = max(0.0, 0.412424 * r + 0.357579 * g + 0.180464 * b)
        dst[j + 1] = max(0.0, 0.212656 * r + 0.715158 * g + 0.0721856 * b)
        dst[j + 2] = max(0.0, 0.0193324 * r + 0.119193 * g + 0.950444 * b)
    return 0


def srgb_gamma(v: Float64) -> Float64:
    if v <= 0.0031308:
        return v * 12.92
    return 1.055 * (v ** (1.0 / 2.4)) - 0.055


@export("mcm_xyz_to_srgb")
def mcm_xyz_to_srgb(src_addr: Int, dst_addr: Int, n: Int) abi("C") -> Int32:
    if n < 0 or (n > 0 and (src_addr == 0 or dst_addr == 0)):
        return 1
    if n == 0:
        return 0
    var src = p(src_addr)
    var dst = p(dst_addr)
    for i in range(n):
        var j = 3 * i
        var x = src[j]
        var y = src[j + 1]
        var z = src[j + 2]
        var r = max(0.0, 3.24071 * x - 1.53726 * y - 0.498571 * z)
        var g = max(0.0, -0.969258 * x + 1.87599 * y + 0.0415557 * z)
        var b = max(0.0, 0.0556352 * x - 0.203996 * y + 1.05707 * z)
        dst[j] = srgb_gamma(r)
        dst[j + 1] = srgb_gamma(g)
        dst[j + 2] = srgb_gamma(b)
    return 0


@export("mcm_transform3")
def mcm_transform3(
    src_addr: Int, dst_addr: Int, matrix_addr: Int, n: Int
) abi("C") -> Int32:
    if n < 0 or (n > 0 and (src_addr == 0 or dst_addr == 0 or matrix_addr == 0)):
        return 1
    if n == 0:
        return 0
    var src = p(src_addr)
    var dst = p(dst_addr)
    var m = p(matrix_addr)
    for i in range(n):
        var j = 3 * i
        var x = src[j]
        var y = src[j + 1]
        var z = src[j + 2]
        dst[j] = m[0] * x + m[1] * y + m[2] * z
        dst[j + 1] = m[3] * x + m[4] * y + m[5] * z
        dst[j + 2] = m[6] * x + m[7] * y + m[8] * z
    return 0
