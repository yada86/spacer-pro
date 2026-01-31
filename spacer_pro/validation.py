# spacer_pro/validation.py
# =============================================================================
#  Spacer PRO – QA / Validation Layer (Stage 1)
#  Passive checks only: never mutates scene/props, never blocks by default.
#  Exception-safe by design.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass(frozen=True)
class ValidationMessage:
    level: str   # "INFO" | "WARNING" | "ERROR"
    scope: str   # "dimensions" | "chamfers" | "taper" | "presets" | "general"
    code: str
    text: str


def _get_num(props: Any, *names: str) -> Optional[float]:
    """Try multiple attribute names; return float if found and convertible."""
    for n in names:
        try:
            v = getattr(props, n, None)
            if v is None:
                continue
            # Blender props can be int/float; also guard against strings.
            f = float(v)
            return f
        except Exception:
            continue
    return None


def _get_bool(props: Any, *names: str) -> Optional[bool]:
    for n in names:
        try:
            v = getattr(props, n, None)
            if v is None:
                continue
            return bool(v)
        except Exception:
            continue
    return None


def _scan_chamfer_values(props: Any) -> List[float]:
    """
    Collect likely chamfer widths/sizes without knowing exact property names.

    Supports both:
      - names containing 'chamfer' (e.g. chamfer_top_outer_width)
      - compact naming like 'ch_ti_size', 'ch_bo_size', etc.
    """
    vals: List[float] = []
    try:
        keys = dir(props)
    except Exception:
        return vals

    for k in keys:
        lk = k.lower()

        # Accept both verbose and compact conventions
        is_chamferish = ("chamfer" in lk) or lk.startswith("ch_") or ("_ch_" in lk)

        if not is_chamferish:
            continue

        # Prefer size/width/amount-style numeric fields
        if not any(tok in lk for tok in ("size", "width", "amount", "len", "length", "dist", "offset")):
            continue

        try:
            v = getattr(props, k, None)
            if v is None:
                continue
            f = float(v)
            if f > 0:
                vals.append(f)
        except Exception:
            continue

    return vals


def _scan_taper_enable(props: Any) -> bool:
    """
    Try to detect taper enable boolean from unknown property naming.
    Looks for names containing 'taper' or starting with 'tp_' and containing enable/on/active.
    """
    try:
        found_any = False
        for k in dir(props):
            lk = k.lower()
            if ("taper" in lk or lk.startswith("tp_") or "_tp_" in lk):
                if any(tok in lk for tok in ("enable", "enabled", "on", "active", "use")):
                    v = getattr(props, k, None)
                    if v is None:
                        continue
                    found_any = True
                    if bool(v):
                        return True
        if found_any:
            return False
    except Exception:
        pass

    # Fallback to common names (only accept real bool-ish values)
    for n in ("taper_enable", "taper_enabled", "enable_taper", "use_taper"):
        try:
            v = getattr(props, n, None)
            if v is None:
                continue
            if isinstance(v, bool):
                return v
            if isinstance(v, int) and v in (0, 1):
                return bool(v)
        except Exception:
            continue

    return False


def _scan_taper_amount(props: Any) -> Optional[float]:
    """
    Detect taper amount/offset in mm (best effort).
    Looks for names containing 'taper' or 'tp_' and amount/mm/offset/dist/size/depth.
    """
    try:
        for k in dir(props):
            lk = k.lower()
            if ("taper" in lk or lk.startswith("tp_") or "_tp_" in lk):
                if any(tok in lk for tok in ("amount", "mm", "offset", "dist", "distance", "size", "delta", "depth")):
                    v = getattr(props, k, None)
                    if v is None:
                        continue
                    f = float(v)
                    # allow negative taper; keep non-zero
                    if abs(f) > 0:
                        return f
    except Exception:
        pass

    return _get_num(props, "taper_amount", "taper_mm", "taper_offset", "taper_dist", "taper_size")


def _scan_taper_angle(props: Any) -> Optional[float]:
    """
    Detect taper angle in degrees (best effort).
    Looks for names with taper + angle/deg.
    """
    try:
        for k in dir(props):
            lk = k.lower()
            if ("taper" in lk or lk.startswith("tp_") or "_tp_" in lk):
                if any(tok in lk for tok in ("angle", "deg")):
                    v = getattr(props, k, None)
                    if v is None:
                        continue
                    f = float(v)
                    if abs(f) > 0:
                        return f
    except Exception:
        pass

    return _get_num(props, "taper_angle", "taper_deg", "taper_angle_deg")


def validate_props(props: Any, scopes: Optional[set[str]] = None) -> List[ValidationMessage]:
    """
    Passive validation for Spacer PRO props.
    Returns list of ValidationMessage.
    Never raises.
    """
    msgs: List[ValidationMessage] = []
    if not props:
        return msgs

    try:
        # Common outer dimensions (ring/cylinder)
        od = _get_num(props, "outer_diameter", "od", "outer_diam", "outer_radius")  # radius handled below
        idv = _get_num(props, "inner_diameter", "id", "inner_diam", "inner_radius")  # radius handled below

        # If user stores radius, interpret consistently:
        # If both look like radii (small numbers) we can't know; we only convert when name says radius.
        od_r = _get_num(props, "outer_radius")
        id_r = _get_num(props, "inner_radius")
        if od is None and od_r is not None:
            od = od_r * 2.0
        if idv is None and id_r is not None:
            idv = id_r * 2.0

        # Common outer size for non-round primitives
        out_x = _get_num(props, "outer_x", "size_x", "outer_size_x", "outer_width", "width")
        out_y = _get_num(props, "outer_y", "size_y", "outer_size_y", "outer_depth", "depth")
        height = _get_num(props, "height", "thickness", "z", "size_z", "outer_z")

        # Common cutout sizes
        cut_x = _get_num(props, "cutout_x", "inner_x", "hole_x", "cut_x", "slot_x")
        cut_y = _get_num(props, "cutout_y", "inner_y", "hole_y", "cut_y", "slot_y")
        cut_r = _get_num(props, "cutout_radius", "inner_radius", "hole_radius", "cutout_r")
        cut_d = _get_num(props, "cutout_diameter", "inner_diameter", "hole_diameter", "cutout_d")

        # --- Basic sanity checks ---
        for name, val in (("outer_diameter", od), ("inner_diameter", idv), ("outer_x", out_x), ("outer_y", out_y), ("height", height)):
            if val is not None and val <= 0:
                msgs.append(ValidationMessage("ERROR", "dimensions", "DIM_NONPOSITIVE", f"{name} must be > 0."))

        if od is not None and idv is not None and idv >= od:
            msgs.append(ValidationMessage("ERROR", "dimensions", "ID_GE_OD", "Inner diameter must be smaller than outer diameter."))

        if out_x is not None and cut_x is not None and cut_x >= out_x:
            msgs.append(ValidationMessage("ERROR", "dimensions", "CUTOUT_X_GE_OUTER_X", "Cutout X must be smaller than outer X."))

        if out_y is not None and cut_y is not None and cut_y >= out_y:
            msgs.append(ValidationMessage("ERROR", "dimensions", "CUTOUT_Y_GE_OUTER_Y", "Cutout Y must be smaller than outer Y."))

        # --- Wall thickness check (mechanical baseline) ---
        # Ring wall thickness (radial): (OD - ID)/2
        wall = None
        if od is not None and idv is not None:
            wall = (od - idv) * 0.5
            if wall <= 0:
                msgs.append(ValidationMessage("ERROR", "dimensions", "WALL_LE_ZERO", "Computed wall thickness is <= 0. Check OD/ID."))
            else:
                # Conservative baseline; tune later via settings if needed
                if wall < 0.8:
                    msgs.append(ValidationMessage("WARNING", "dimensions", "WALL_THIN", f"Wall thickness is low (~{wall:.2f} mm). Consider >= 0.8 mm for strength."))

        # Rectangular wall thickness (approx): (outer - cutout)/2 on each axis
        if out_x is not None and cut_x is not None:
            wx = (out_x - cut_x) * 0.5
            if wx <= 0:
                msgs.append(ValidationMessage("ERROR", "dimensions", "WALL_X_LE_ZERO", "Computed X wall thickness is <= 0."))
            elif wx < 0.8:
                msgs.append(ValidationMessage("WARNING", "dimensions", "WALL_X_THIN", f"X wall thickness is low (~{wx:.2f} mm)."))

        if out_y is not None and cut_y is not None:
            wy = (out_y - cut_y) * 0.5
            if wy <= 0:
                msgs.append(ValidationMessage("ERROR", "dimensions", "WALL_Y_LE_ZERO", "Computed Y wall thickness is <= 0."))
            elif wy < 0.8:
                msgs.append(ValidationMessage("WARNING", "dimensions", "WALL_Y_THIN", f"Y wall thickness is low (~{wy:.2f} mm)."))

        # --- Chamfer too large check ---
        # Prefer explicit per-corner checks if compact Spacer PRO properties exist.
        # This enables stable codes like CH_TI_* for inline per-parameter UI warnings.
        corner_prop = {
            "TI": "ch_ti_size",
            "TO": "ch_to_size",
            "BI": "ch_bi_size",
            "BO": "ch_bo_size",
        }
        corner_label = {
            "TI": "Top Inner",
            "TO": "Top Outer",
            "BI": "Bottom Inner",
            "BO": "Bottom Outer",
        }

        corner_sizes: dict[str, float] = {}
        for c, prop_name in corner_prop.items():
            try:
                if hasattr(props, prop_name):
                    v = getattr(props, prop_name)
                    f = float(v)
                    if f > 0:
                        corner_sizes[c] = f
            except Exception:
                continue

        if corner_sizes:
            for c, csz in corner_sizes.items():
                if wall is not None and wall > 0 and csz > wall:
                    msgs.append(ValidationMessage(
                        "WARNING", "chamfers", f"CH_{c}_GT_WALL",
                        f"{corner_label.get(c, c)} chamfer (~{csz:.2f} mm) exceeds wall (~{wall:.2f} mm). Risk of self-intersection."
                    ))
                if height is not None and height > 0 and csz > height:
                    msgs.append(ValidationMessage(
                        "WARNING", "chamfers", f"CH_{c}_GT_HEIGHT",
                        f"{corner_label.get(c, c)} chamfer (~{csz:.2f} mm) exceeds height (~{height:.2f} mm)."
                    ))
        else:
            # Fallback heuristic for unknown property schemas.
            chamfers = _scan_chamfer_values(props)
            if chamfers:
                cmax = max(chamfers)
                if wall is not None and wall > 0 and cmax > wall:
                    msgs.append(ValidationMessage(
                        "WARNING", "chamfers", "CHAMFER_GT_WALL",
                        f"Chamfer (~{cmax:.2f} mm) exceeds wall (~{wall:.2f} mm). Risk of self-intersection."
                    ))
                if height is not None and height > 0 and cmax > height:
                    msgs.append(ValidationMessage(
                        "WARNING", "chamfers", "CHAMFER_GT_HEIGHT",
                        f"Chamfer (~{cmax:.2f} mm) exceeds height (~{height:.2f} mm)."
                    ))

        # --- Cutout vs outer round check (if only diameters known) ---
        # If cutout diameter exists and outer diameter exists
        if od is not None:
            if cut_d is not None and cut_d >= od:
                msgs.append(ValidationMessage("ERROR", "dimensions", "CUTOUT_D_GE_OD", "Cutout diameter must be smaller than outer diameter."))
            if cut_r is not None and (cut_r * 2.0) >= od:
                msgs.append(ValidationMessage("ERROR", "dimensions", "CUTOUT_R_GE_OD", "Cutout radius is too large for outer diameter."))

        # --- Taper checks (basic, name-robust) ---
        taper_on = _scan_taper_enable(props)
        taper_amt = _scan_taper_amount(props)
        taper_ang = _scan_taper_angle(props)

        if taper_on:
            # Prefer explicit Spacer PRO per-corner naming if present.
            # These are the actual properties observed in Blender: tp_ti_depth, tp_ti_angle, etc.
            # Emit TP_{CORNER}_* codes so UI can show inline warnings per corner.
            explicit_seen = False

            def _tp_check(corner_tag: str, corner_label: str) -> None:
                nonlocal explicit_seen
                c = corner_tag.lower()
                on_val = _get_bool(props, f"tp_{c}_on")
                depth_val = _get_num(props, f"tp_{c}_depth")
                ang_val = _get_num(props, f"tp_{c}_angle")

                is_on = bool(on_val) if on_val is not None else bool((depth_val or 0) != 0 or (ang_val or 0) != 0)
                if not is_on:
                    return

                if depth_val is not None:
                    explicit_seen = True
                    if depth_val > 0 and height is not None and height > 0:
                        if depth_val > height:
                            msgs.append(ValidationMessage(
                                "WARNING", "taper", f"TP_{corner_tag}_DEPTH_GT_HEIGHT",
                                f"{corner_label} taper depth (~{depth_val:.2f} mm) exceeds height (~{height:.2f} mm)."
                            ))
                        elif depth_val > (height * 0.5):
                            msgs.append(ValidationMessage(
                                "WARNING", "taper", f"TP_{corner_tag}_DEPTH_HIGH",
                                f"{corner_label} taper depth (~{depth_val:.2f} mm) is high vs height (~{height:.2f} mm)."
                            ))

                if ang_val is not None:
                    explicit_seen = True
                    if ang_val <= 0 or ang_val >= 89.9:
                        msgs.append(ValidationMessage(
                            "WARNING", "taper", f"TP_{corner_tag}_ANGLE_EXTREME",
                            f"{corner_label} taper angle ({ang_val:.2f}°) is extreme. Risk of self-intersection or thin walls."
                        ))
                    elif ang_val >= 70:
                        msgs.append(ValidationMessage(
                            "WARNING", "taper", f"TP_{corner_tag}_ANGLE_HIGH",
                            f"{corner_label} taper angle ({ang_val:.2f}°) is high. Watch wall thickness."
                        ))

            _tp_check("TI", "Top Inner")
            _tp_check("TO", "Top Outer")
            _tp_check("BI", "Bottom Inner")
            _tp_check("BO", "Bottom Outer")

            # Amount vs height sanity
            if not explicit_seen and taper_amt is not None and height is not None and height > 0:
                if abs(taper_amt) > height:
                    msgs.append(ValidationMessage(
                        "WARNING", "taper", "TAPER_GT_HEIGHT",
                        f"Taper amount (~{taper_amt:.2f} mm) exceeds height (~{height:.2f} mm)."
                    ))
                elif abs(taper_amt) > (height * 0.5):
                    msgs.append(ValidationMessage(
                        "WARNING", "taper", "TAPER_HIGH",
                        f"Taper amount (~{taper_amt:.2f} mm) is high vs height (~{height:.2f} mm)."
                    ))

            # Angle sanity (guidance)
            if not explicit_seen and taper_ang is not None:
                if taper_ang <= 0 or taper_ang >= 89.9:
                    msgs.append(ValidationMessage(
                        "WARNING", "taper", "TAPER_ANGLE_EXTREME",
                        f"Taper angle ({taper_ang:.2f}°) is extreme. Risk of self-intersection or thin walls."
                    ))
                elif taper_ang >= 70:
                    msgs.append(ValidationMessage(
                        "WARNING", "taper", "TAPER_ANGLE_HIGH",
                        f"Taper angle ({taper_ang:.2f}°) is high. Watch wall thickness."
                    ))

        # --- Non-blocking info for missing presets/props is not handled here (QA only) ---

    except Exception:
        # Never crash UI; worst case: no messages.
        return msgs

    if scopes is not None:
        try:
            msgs = [m for m in msgs if m.scope in scopes]
        except Exception:
            return []

    return msgs


def draw_validation_box(layout, props: Any, scope: str = "general", title: str = "QA") -> None:
    """
    UI helper: draw a validation box for a specific scope.
    Safe: never raises, never mutates.
    """
    try:
        msgs_all = validate_props(props)
        msgs = [m for m in msgs_all if m.scope == scope]
        if not msgs:
            return

        has_err = any(m.level == "ERROR" for m in msgs)
        has_warn = any(m.level == "WARNING" for m in msgs)

        box = layout.box()
        row = box.row()
        icon = "ERROR" if has_err else ("ERROR" if has_warn else "INFO")
        row.label(text=title, icon=icon)

        for m in msgs[:6]:
            ic = "CANCEL" if m.level == "ERROR" else ("ERROR" if m.level == "WARNING" else "INFO")
            box.label(text=m.text, icon=ic)

        if len(msgs) > 6:
            box.label(text=f"...and {len(msgs) - 6} more", icon="DOT")

    except Exception:
        return


def draw_param_validation(layout, props: Any, *, scope: str, code_prefix: str, title: str = "") -> None:
    """
    Draw small inline warnings for a specific parameter group.
    Filters messages by scope and code prefix (e.g. 'CH_TI_' for Top Inner).
    """
    try:
        msgs_all = validate_props(props)
        msgs = [m for m in msgs_all if m.scope == scope and m.code.startswith(code_prefix)]
        if not msgs:
            return

        box = layout.box()
        if title:
            row = box.row()
            row.label(text=title, icon="ERROR")

        for m in msgs[:3]:
            ic = "CANCEL" if m.level == "ERROR" else ("ERROR" if m.level == "WARNING" else "INFO")
            box.label(text=m.text, icon=ic)

    except Exception:
        return
