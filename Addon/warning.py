"""Pulsing viewport warning shown while editing/sculpting a non-basis shape key."""

import bpy
import blf
import time
import math

_draw_handle = None
_timer_running = False

# Modes in which the active shape key can be modified and is therefore
# worth warning about.
_WARN_MODES = {'EDIT', 'SCULPT'}

_ANCHOR_ITEMS = [
    ('TOP_LEFT',     "Top Left",     ""),
    ('TOP_CENTER',   "Top Center",   ""),
    ('TOP_RIGHT',    "Top Right",    ""),
    ('MIDDLE_LEFT',  "Middle Left",  ""),
    ('CENTER',       "Center",       ""),
    ('MIDDLE_RIGHT', "Middle Right", ""),
    ('BOTTOM_LEFT',  "Bottom Left",  ""),
    ('BOTTOM_CENTER',"Bottom Center",""),
    ('BOTTOM_RIGHT', "Bottom Right", ""),
]


def get_prefs():
    # __package__ is the top-level addon package (e.g. "mirror_shape_key_extension")
    addon = bpy.context.preferences.addons.get(__package__)
    if addon:
        return addon.preferences
    return None


def warning_active(context, prefs):
    if prefs is None or not prefs.enabled:
        return False
    obj = context.active_object
    if not obj or obj.type != 'MESH':
        return False
    if obj.mode not in _WARN_MODES:
        return False
    if not obj.data.shape_keys:
        return False
    if obj.active_shape_key_index == 0:
        return False
    return True


def draw_warning_callback():
    context = bpy.context
    prefs = get_prefs()
    if not warning_active(context, prefs):
        return

    obj = context.active_object
    sk = obj.active_shape_key
    if sk is None:
        return

    # Message
    try:
        text = prefs.message.format(shapekey=sk.name)
    except (KeyError, IndexError, ValueError):
        text = prefs.message

    # Pulse
    phase = 0.5 + 0.5 * math.sin(2.0 * math.pi * time.time() * prefs.pulse_speed)
    alpha = prefs.alpha_min + (prefs.alpha_max - prefs.alpha_min) * phase

    font_id = 0
    blf.size(font_id, prefs.font_size)

    # Measure text so we can align it
    text_w, text_h = blf.dimensions(font_id, text)

    # Get current viewport region size (fall back to window size)
    region = context.region
    if region is not None:
        reg_w, reg_h = region.width, region.height
    else:
        win = context.window
        reg_w, reg_h = (win.width, win.height) if win else (1920, 1080)

    # Normalized -> pixel (blf origin is bottom-left of the region)
    px = prefs.pos_x * reg_w
    py = prefs.pos_y * reg_h

    # Apply anchor offset
    anchor = prefs.anchor
    if 'LEFT' in anchor:
        off_x = 0
    elif 'RIGHT' in anchor:
        off_x = -text_w
    else:  # CENTER
        off_x = -text_w * 0.5

    if 'TOP' in anchor:
        off_y = -text_h
    elif 'BOTTOM' in anchor:
        off_y = 0
    else:  # MIDDLE / CENTER
        off_y = -text_h * 0.5

    blf.color(font_id, 1.0, 0.0, 0.0, alpha)
    blf.position(font_id, px + off_x, py + off_y, 0)
    blf.draw(font_id, text)


def tag_redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def timer_update():
    prefs = get_prefs()
    if warning_active(bpy.context, prefs):
        tag_redraw()
        return 0.033
    return 0.5


class ShapeKeyWarningPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    enabled: bpy.props.BoolProperty(
        name="Enable Edit Warning",
        description=(
            "Show a pulsing warning while editing or sculpting a "
            "non-basis shape key"
        ),
        default=True,
    )
    pos_x: bpy.props.FloatProperty(
        name="X (0-1)",
        description="Horizontal position as a fraction of the viewport width",
        default=0.5, min=0.0, max=1.0,
        precision=3, subtype='FACTOR',
    )
    pos_y: bpy.props.FloatProperty(
        name="Y (0-1)",
        description="Vertical position as a fraction of the viewport height (0 = bottom)",
        default=0.95, min=0.0, max=1.0,
        precision=3, subtype='FACTOR',
    )
    anchor: bpy.props.EnumProperty(
        name="Anchor",
        description="Which corner of the text box is placed at the target position",
        items=_ANCHOR_ITEMS,
        default='TOP_CENTER',
    )
    font_size: bpy.props.IntProperty(
        name="Font Size",
        default=18, min=8, max=100,
    )
    message: bpy.props.StringProperty(
        name="Message",
        description="Use {shapekey} to insert the active shape key name",
        default='"{shapekey}" shape key selected!',
    )
    pulse_speed: bpy.props.FloatProperty(
        name="Pulse Speed (Hz)",
        default=1.0, min=0.1, max=5.0,
    )
    alpha_min: bpy.props.FloatProperty(
        name="Min Opacity",
        default=0.1, min=0.0, max=1.0,
    )
    alpha_max: bpy.props.FloatProperty(
        name="Max Opacity",
        default=1.0, min=0.0, max=1.0,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "enabled")
        box = layout.box()
        box.label(text="Warning Position (normalized viewport coords)")
        col = box.column(align=True)
        col.prop(self, "pos_x")
        col.prop(self, "pos_y")
        col.prop(self, "anchor")
        layout.prop(self, "font_size")
        layout.prop(self, "message")
        layout.prop(self, "pulse_speed")
        row = layout.row(align=True)
        row.prop(self, "alpha_min")
        row.prop(self, "alpha_max")


def register():
    bpy.utils.register_class(ShapeKeyWarningPreferences)

    global _draw_handle, _timer_running
    _draw_handle = bpy.types.SpaceView3D.draw_handler_add(
        draw_warning_callback, (), 'WINDOW', 'POST_PIXEL'
    )
    if not _timer_running:
        bpy.app.timers.register(timer_update, first_interval=0.1)
        _timer_running = True


def unregister():
    global _draw_handle, _timer_running
    if _draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, 'WINDOW')
        _draw_handle = None
    if _timer_running:
        try:
            bpy.app.timers.unregister(timer_update)
        except ValueError:
            pass
        _timer_running = False

    bpy.utils.unregister_class(ShapeKeyWarningPreferences)