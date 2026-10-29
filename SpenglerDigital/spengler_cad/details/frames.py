"""Lokale Koordinatensysteme als 4×4-Matrizen (Zeilenliste, mm) – reine Rechnung, ohne Fusion testbar.

Die Ausrichtung einer Detailvorlage auf eine Zielkante ist:  T = Ziel · Anker⁻¹
(Anker = Rahmen der Anschlusskante im Quellmodell, Ziel = Rahmen der gewählten Kante).
"""
import math


def norm(v):
    L = math.sqrt(sum(c * c for c in v))
    if L < 1e-12:
        raise ValueError("Nullvektor")
    return [c / L for c in v]


def kreuz(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def rahmen_aus_kante(start, ende, flaechennormale):
    """Rahmen: Ursprung = Kantenanfang, x = Kantenrichtung, z = Flächennormale (senkrecht zu x gemacht), y = z × x."""
    x = norm([e - s for s, e in zip(start, ende)])
    n = list(flaechennormale)
    d = sum(a * b for a, b in zip(n, x))
    z = norm([a - d * b for a, b in zip(n, x)])
    y = kreuz(z, x)
    return {"origin": list(start), "x": x, "y": y, "z": z}


def matrix(frame):
    o, x, y, z = frame["origin"], frame["x"], frame["y"], frame["z"]
    return [[x[0], y[0], z[0], o[0]], [x[1], y[1], z[1], o[1]], [x[2], y[2], z[2], o[2]], [0.0, 0.0, 0.0, 1.0]]


def invers_starr(m):
    r = [[m[j][i] for j in range(3)] for i in range(3)]
    t = [-sum(r[i][j] * m[j][3] for j in range(3)) for i in range(3)]
    return [r[0] + [t[0]], r[1] + [t[1]], r[2] + [t[2]], [0.0, 0.0, 0.0, 1.0]]


def mal(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def ausrichtung(anker, ziel):
    return mal(matrix(ziel), invers_starr(matrix(anker)))


def anwenden(m, p):
    return [sum(m[i][j] * p[j] for j in range(3)) + m[i][3] for i in range(3)]
