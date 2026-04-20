from enum import Enum
from typing import Any
import math
import time
from datetime import datetime

from scripts.logging_config import get_utility_logger

logger = get_utility_logger('tools.svg_path_tool')


class PathEquation(str, Enum):
    PARABOLIC = "PARABOLIC"
    CIRCULAR = "CIRCULAR"
    ELLIPTICAL = "ELLIPTICAL"
    SINE_WAVE = "SINE_WAVE"
    SPIRAL = "SPIRAL"
    S_CURVE = "S_CURVE"
    LINEAR = "LINEAR"
    ARC = "ARC"
    BEZIER = "BEZIER"
    ZIGZAG = "ZIGZAG"
    BOUNCE = "BOUNCE"
    SPLINE = "SPLINE"


# === Path creator functions (Python versions of your TS helpers) ===

def create_parabolic_path(
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    arc_height: float
) -> str:
    control_x = (start_x + end_x) / 2.0
    control_y = min(start_y, end_y) - arc_height
    return f"M {start_x} {start_y} Q {control_x} {control_y} {end_x} {end_y}"


def create_circular_path(
    center_x: float,
    center_y: float,
    radius: float
) -> str:
    # Two arcs to complete circle
    d = (
        f"M {center_x - radius} {center_y} "
        f"A {radius} {radius} 0 0 1 {center_x + radius} {center_y} "
        f"A {radius} {radius} 0 0 1 {center_x - radius} {center_y}"
    )
    return d


def create_elliptical_path(
    center_x: float,
    center_y: float,
    radius_x: float,
    radius_y: float
) -> str:
    d = (
        f"M {center_x - radius_x} {center_y} "
        f"A {radius_x} {radius_y} 0 0 1 {center_x + radius_x} {center_y} "
        f"A {radius_x} {radius_y} 0 0 1 {center_x - radius_x} {center_y}"
    )
    return d


def create_sine_wave_path(
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    amplitude: float,
    cycles: int
) -> str:
    """
    Create sine wave from start to end point.
    Direction is determined by the start→end vector.
    Amplitude is perpendicular to the direction of travel.
    """
    # Calculate direction vector
    dx = end_x - start_x
    dy = end_y - start_y
    length = math.sqrt(dx * dx + dy * dy)

    if length == 0:
        return f"M {start_x} {start_y}"

    # Unit vectors: forward (along path) and perpendicular (for amplitude)
    fx, fy = dx / length, dy / length  # forward unit vector
    px, py = -fy, fx  # perpendicular unit vector (90° counter-clockwise)

    # Wavelength derived from total length and cycles
    wavelength = length / cycles

    d = [f"M {start_x} {start_y}"]
    direction = 1.0

    for i in range(cycles):
        # Progress along the path
        t_mid = (i + 0.5) / cycles
        t_end = (i + 1) / cycles

        # Mid point (control point for quadratic curve)
        mid_x = start_x + dx * t_mid + px * amplitude * direction
        mid_y = start_y + dy * t_mid + py * amplitude * direction

        # End point of this cycle segment
        seg_end_x = start_x + dx * t_end
        seg_end_y = start_y + dy * t_end

        d.append(f"Q {mid_x} {mid_y} {seg_end_x} {seg_end_y}")
        direction *= -1.0

    return " ".join(d)


def create_spiral_path(
    center_x: float,
    center_y: float,
    max_radius: float,
    revolutions: float,
    points: int = 100,
    inward: bool = False
) -> str:
    path_parts = []
    for i in range(points + 1):
        t = i / points  # 0 → 1
        angle = t * revolutions * 2.0 * math.pi
        if inward:
            radius = (1 - t) * max_radius  # starts at max_radius, shrinks to center
        else:
            radius = t * max_radius  # starts at center, grows to max_radius
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        if i == 0:
            path_parts.append(f"M {x} {y}")
        else:
            path_parts.append(f"L {x} {y}")
    return " ".join(path_parts)


def create_s_curve_path(
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    curvature: float = 0.5
) -> str:
    dx = end_x - start_x
    dy = end_y - start_y
    cp1_x = start_x + dx * curvature
    cp1_y = start_y
    cp2_x = end_x - dx * curvature
    cp2_y = end_y
    return (
        f"M {start_x} {start_y} "
        f"C {cp1_x} {cp1_y} {cp2_x} {cp2_y} {end_x} {end_y}"
    )


def create_linear_path(
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float
) -> str:
    return f"M {start_x} {start_y} L {end_x} {end_y}"


def create_arc_path(
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    radius: float,
    sweep: int = 0,
    large_arc: int = 0
) -> str:
    """
    sweep: 0=UP, 1=DOWN, 2=LEFT, 3=RIGHT
    Converts to SVG sweep based on arc direction.
    """
    dx = end_x - start_x
    dy = end_y - start_y
    is_horizontal = abs(dx) >= abs(dy)
    going_right = dx > 0
    going_down = dy > 0

    if is_horizontal:
        if sweep == 0:  # UP
            svg_sweep = 1 if going_right else 0
        else:  # DOWN (1)
            svg_sweep = 0 if going_right else 1
    else:
        if sweep == 2:  # LEFT
            svg_sweep = 0 if going_down else 1
        else:  # RIGHT (3)
            svg_sweep = 1 if going_down else 0

    return f"M {start_x} {start_y} A {radius} {radius} 0 {large_arc} {svg_sweep} {end_x} {end_y}"


def create_bezier_path(
    start_x: float,
    start_y: float,
    cp1_x: float,
    cp1_y: float,
    cp2_x: float,
    cp2_y: float,
    end_x: float,
    end_y: float
) -> str:
    return f"M {start_x} {start_y} C {cp1_x} {cp1_y} {cp2_x} {cp2_y} {end_x} {end_y}"


def create_zigzag_path(
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    amplitude: float,
    segments: int
) -> str:
    """
    Create zigzag path from start to end point.
    Direction is determined by the start→end vector.
    Amplitude is perpendicular to the direction of travel.
    """
    # Calculate direction vector
    dx = end_x - start_x
    dy = end_y - start_y
    length = math.sqrt(dx * dx + dy * dy)

    if length == 0:
        return f"M {start_x} {start_y}"

    # Perpendicular unit vector (for amplitude)
    px, py = -dy / length, dx / length

    d = [f"M {start_x} {start_y}"]
    direction = 1.0

    for i in range(segments):
        # Progress along the path
        t = (i + 1) / segments

        # Point along the main direction + perpendicular offset
        x = start_x + dx * t + px * amplitude * direction
        y = start_y + dy * t + py * amplitude * direction

        d.append(f"L {x} {y}")
        direction *= -1.0

    return " ".join(d)


def create_bounce_path(
    start_x: float,
    start_y: float,
    end_x: float,
    ground_y: float,
    initial_height: float,
    bounces: int,
    decay: float = 0.6
) -> str:
    d = [f"M {start_x} {start_y}"]
    total_distance = end_x - start_x
    bounce_distance = total_distance / (bounces + 1)
    x = start_x
    height = initial_height

    for i in range(bounces + 1):
        next_x = x + bounce_distance
        control_x = (x + next_x) / 2.0
        control_y = ground_y - height
        d.append(f"Q {control_x} {control_y} {next_x} {ground_y}")
        x = next_x
        height *= decay

    return " ".join(d)


def create_spline_path(
    points: list,
    tension: float = 0.3
) -> str:
    """
    Create smooth curve through N points using Catmull-Rom to Bezier conversion.
    points: list of [x, y] pairs, e.g. [[100,100], [200,50], [300,150], [400,100]]
    tension: 0 = sharp corners, 1 = very smooth (default 0.3)
    """
    if len(points) < 2:
        raise ValueError("Spline requires at least 2 points")

    if len(points) == 2:
        return f"M {points[0][0]} {points[0][1]} L {points[1][0]} {points[1][1]}"

    d = [f"M {points[0][0]} {points[0][1]}"]

    for i in range(len(points) - 1):
        p0 = points[i - 1] if i > 0 else points[0]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else points[-1]

        # Catmull-Rom to Bezier control points
        cp1_x = p1[0] + (p2[0] - p0[0]) * tension
        cp1_y = p1[1] + (p2[1] - p0[1]) * tension
        cp2_x = p2[0] - (p3[0] - p1[0]) * tension
        cp2_y = p2[1] - (p3[1] - p1[1]) * tension

        d.append(f"C {cp1_x} {cp1_y} {cp2_x} {cp2_y} {p2[0]} {p2[1]}")

    return " ".join(d)


def get_path(equation: str, **params: Any) -> str:
    """
    Generate SVG path 'd' attribute for a predefined path type.

    Parameters
    ----------
    equation : str
        Name of the path equation (e.g. "PARABOLIC", "CIRCULAR").
    **params :
        Path-specific parameters:
        - PARABOLIC: start_x, start_y, end_x, end_y, arc_height
        - CIRCULAR: center_x, center_y, radius
        - ELLIPTICAL: center_x, center_y, radius_x, radius_y
        - SINE_WAVE: start_x, start_y, end_x, end_y, amplitude, cycles
        - SPIRAL: center_x, center_y, max_radius, revolutions, [points]
        - S_CURVE: start_x, start_y, end_x, end_y, [curvature]
        - LINEAR: start_x, start_y, end_x, end_y
        - ARC: start_x, start_y, end_x, end_y, radius, [sweep], [large_arc]
        - BEZIER: start_x, start_y, cp1_x, cp1_y, cp2_x, cp2_y, end_x, end_y
        - ZIGZAG: start_x, start_y, end_x, end_y, amplitude, segments
        - BOUNCE: start_x, start_y, end_x, ground_y, initial_height, bounces, [decay]
        - SPLINE: points (array of [x,y] pairs), [tension]

    Returns
    -------
    str
        SVG path 'd' attribute string.
    """
    func_start = time.time()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    logger.debug(f"[GET_PATH] >>> FUNCTION ENTRY at {timestamp}")
    logger.debug(f"[GET_PATH] Raw equation input: '{equation}' (type: {type(equation).__name__})")
    logger.debug(f"[GET_PATH] Raw params: {params}")
    logger.debug(f"[GET_PATH] Params count: {len(params)}")

    logger.debug(f"[GET_PATH] Step 1: Converting equation to uppercase...")
    equation_upper = equation.upper()
    logger.debug(f"[GET_PATH] Equation after upper(): '{equation_upper}'")

    logger.debug(f"[GET_PATH] Step 2: Validating equation against PathEquation enum...")
    try:
        eq_enum = PathEquation(equation_upper)
        logger.debug(f"[GET_PATH] Successfully matched enum: {eq_enum}")
        logger.debug(f"[GET_PATH] Enum value: {eq_enum.value}")
    except ValueError:
        valid = ", ".join(e.value for e in PathEquation)
        logger.error(f"[GET_PATH] FAILED: Unknown equation '{equation}'")
        logger.error(f"[GET_PATH] Valid equations: {valid}")
        raise ValueError(f"Unknown equation '{equation}'. Valid: {valid}")

    def require_params(required_keys):
        logger.debug(f"[GET_PATH] Checking required params: {required_keys}")
        missing = [k for k in required_keys if k not in params]
        if missing:
            logger.error(f"[GET_PATH] Missing required params: {missing}")
            raise ValueError(
                f"Missing parameters for {eq_enum.value}: {', '.join(missing)}"
            )
        logger.debug(f"[GET_PATH] All required params present")
        for key in required_keys:
            logger.debug(f"[GET_PATH]   {key} = {params[key]} (type: {type(params[key]).__name__})")

    logger.debug(f"[GET_PATH] Step 3: Routing to path creator for {eq_enum.value}...")
    path_start = time.time()
    result = None

    if eq_enum == PathEquation.PARABOLIC:
        logger.debug(f"[GET_PATH] Creating PARABOLIC path...")
        require_params(["start_x", "start_y", "end_x", "end_y", "arc_height"])
        result = create_parabolic_path(
            params["start_x"], params["start_y"],
            params["end_x"], params["end_y"], params["arc_height"]
        )
    elif eq_enum == PathEquation.CIRCULAR:
        logger.debug(f"[GET_PATH] Creating CIRCULAR path...")
        require_params(["center_x", "center_y", "radius"])
        result = create_circular_path(
            params["center_x"], params["center_y"], params["radius"]
        )
    elif eq_enum == PathEquation.ELLIPTICAL:
        logger.debug(f"[GET_PATH] Creating ELLIPTICAL path...")
        require_params(["center_x", "center_y", "radius_x", "radius_y"])
        result = create_elliptical_path(
            params["center_x"], params["center_y"],
            params["radius_x"], params["radius_y"]
        )
    elif eq_enum == PathEquation.SINE_WAVE:
        logger.debug(f"[GET_PATH] Creating SINE_WAVE path...")
        require_params(["start_x", "start_y", "end_x", "end_y", "amplitude", "cycles"])
        cycles_int = int(params["cycles"])
        logger.debug(f"[GET_PATH] Cycles converted to int: {cycles_int}")
        result = create_sine_wave_path(
            params["start_x"], params["start_y"],
            params["end_x"], params["end_y"],
            params["amplitude"], cycles_int
        )
    elif eq_enum == PathEquation.SPIRAL:
        logger.debug(f"[GET_PATH] Creating SPIRAL path...")
        require_params(["center_x", "center_y", "max_radius", "revolutions"])
        points = params.get("points", 100)
        inward = params.get("inward", False)
        logger.debug(f"[GET_PATH] Optional params: points={points}, inward={inward}")
        result = create_spiral_path(
            params["center_x"], params["center_y"],
            params["max_radius"], params["revolutions"],
            points, inward
        )
    elif eq_enum == PathEquation.S_CURVE:
        logger.debug(f"[GET_PATH] Creating S_CURVE path...")
        require_params(["start_x", "start_y", "end_x", "end_y"])
        curvature = params.get("curvature", 0.5)
        logger.debug(f"[GET_PATH] Optional param: curvature={curvature}")
        result = create_s_curve_path(
            params["start_x"], params["start_y"],
            params["end_x"], params["end_y"],
            curvature
        )
    elif eq_enum == PathEquation.LINEAR:
        logger.debug(f"[GET_PATH] Creating LINEAR path...")
        require_params(["start_x", "start_y", "end_x", "end_y"])
        result = create_linear_path(
            params["start_x"], params["start_y"],
            params["end_x"], params["end_y"]
        )
    elif eq_enum == PathEquation.ARC:
        logger.debug(f"[GET_PATH] Creating ARC path...")
        require_params(["start_x", "start_y", "end_x", "end_y", "radius"])
        sweep = params.get("sweep", 0)
        large_arc = params.get("large_arc", 0)
        logger.debug(f"[GET_PATH] Optional params: sweep={sweep}, large_arc={large_arc}")
        result = create_arc_path(
            params["start_x"], params["start_y"],
            params["end_x"], params["end_y"],
            params["radius"], sweep, large_arc
        )
    elif eq_enum == PathEquation.BEZIER:
        logger.debug(f"[GET_PATH] Creating BEZIER path...")
        require_params(["start_x", "start_y", "cp1_x", "cp1_y", "cp2_x", "cp2_y", "end_x", "end_y"])
        result = create_bezier_path(
            params["start_x"], params["start_y"],
            params["cp1_x"], params["cp1_y"],
            params["cp2_x"], params["cp2_y"],
            params["end_x"], params["end_y"]
        )
    elif eq_enum == PathEquation.ZIGZAG:
        logger.debug(f"[GET_PATH] Creating ZIGZAG path...")
        require_params(["start_x", "start_y", "end_x", "end_y", "amplitude", "segments"])
        segments_int = int(params["segments"])
        logger.debug(f"[GET_PATH] Segments converted to int: {segments_int}")
        result = create_zigzag_path(
            params["start_x"], params["start_y"],
            params["end_x"], params["end_y"],
            params["amplitude"], segments_int
        )
    elif eq_enum == PathEquation.BOUNCE:
        logger.debug(f"[GET_PATH] Creating BOUNCE path...")
        require_params(["start_x", "start_y", "end_x", "ground_y", "initial_height", "bounces"])
        decay = params.get("decay", 0.6)
        logger.debug(f"[GET_PATH] Optional param: decay={decay}")
        result = create_bounce_path(
            params["start_x"], params["start_y"],
            params["end_x"], params["ground_y"],
            params["initial_height"], params["bounces"],
            decay
        )
    elif eq_enum == PathEquation.SPLINE:
        logger.debug(f"[GET_PATH] Creating SPLINE path...")
        require_params(["points"])
        tension = params.get("tension", 0.3)
        logger.debug(f"[GET_PATH] Points count: {len(params['points'])}")
        logger.debug(f"[GET_PATH] Optional param: tension={tension}")
        result = create_spline_path(
            params["points"], tension
        )
    else:
        logger.error(f"[GET_PATH] Unsupported equation type: {eq_enum}")
        raise ValueError(f"Unsupported equation type: {eq_enum}")

    path_elapsed = time.time() - path_start
    func_elapsed = time.time() - func_start
    end_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    logger.debug(f"[GET_PATH] Path creation took: {path_elapsed*1000:.2f}ms")
    logger.debug(f"[GET_PATH] Result type: {type(result).__name__}")
    logger.debug(f"[GET_PATH] Result length: {len(result)} chars")
    logger.debug(f"[GET_PATH] Result preview: {result[:500]}{'...' if len(result) > 500 else ''}")
    logger.debug(f"[GET_PATH] Total function time: {func_elapsed*1000:.2f}ms")
    logger.debug(f"[GET_PATH] <<< FUNCTION EXIT at {end_timestamp}")

    return result


def path_equation_to_svg(
    equation: str,              # string referring to PathEquation enum
    color: str,
    style: str,
    thickness: float,
    height: int,
    width: int,
    **params: Any              # extra params for specific path types
) -> str:
    """
    Generate SVG code for a predefined path type.

    Parameters
    ----------
    equation : str
        Name of the path equation (matches PathEquation: e.g. "PARABOLIC").
    color : str
        Stroke color, hex code (e.g. "#ff0000").
    style : str
        Line style: "solid", "dotted", "dashed", "dashdot" (case-insensitive).
    thickness : float
        Stroke width in pixels (e.g. 1, 2, 3).
    height : int
        SVG height in pixels.
    width : int
        SVG width in pixels.
    **params :
        Extra keyword arguments required by each path type:
        - PARABOLIC:
            start_x, start_y, end_x, end_y, arc_height
        - CIRCULAR:
            center_x, center_y, radius
        - ELLIPTICAL:
            center_x, center_y, radius_x, radius_y
        - SINE_WAVE:
            start_x, start_y, end_x, end_y, amplitude, cycles
        - SPIRAL:
            center_x, center_y, max_radius, revolutions, (optional) points
        - S_CURVE:
            start_x, start_y, end_x, end_y, (optional) curvature

    Returns
    -------
    str
        SVG markup string.
    """
    # Get the path d attribute
    d_attr = get_path(equation, **params)

    # Map style -> stroke-dasharray
    dash_map = {
        "solid": "",
        "dotted": "2,4",
        "dashed": "6,4",
        "dashdot": "6,4,2,4",
    }
    dash_pattern = dash_map.get(style.lower(), "")

    # Build stroke-dasharray attribute if needed
    dash_attr = f' stroke-dasharray="{dash_pattern}"' if dash_pattern else ""

    # Generate complete SVG
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <path d="{d_attr}" stroke="{color}" stroke-width="{thickness}" fill="none"{dash_attr}/>
</svg>'''

    return svg


