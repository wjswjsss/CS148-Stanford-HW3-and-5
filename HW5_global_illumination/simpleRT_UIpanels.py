#  simpleRT_panel.py
#
#  Support file for simpleRT render engine.
#
#  Create custom properties and UI panels for
#  easy access to rendering related parameters.
#
#  Updated for HW5.

import bpy

# Custom Properties for SimpleRT materials
class ObjectSettings(bpy.types.PropertyGroup):
    diffuse_color: bpy.props.FloatVectorProperty(
        default=(0.78, 0.78, 0.78), subtype="COLOR"
    )
    specular_color: bpy.props.FloatVectorProperty(
        default=(0.2, 0.2, 0.2), subtype="COLOR"
    )
    specular_hardness: bpy.props.FloatProperty(default=1000.0, soft_min=0.0)
    use_fresnel: bpy.props.BoolProperty(default=False)
    mirror_reflectivity: bpy.props.FloatProperty(
        default=0.0, soft_min=0.0, soft_max=1.0
    )
    ior: bpy.props.FloatProperty(default=1.450)
    transmission: bpy.props.FloatProperty(default=0.0, soft_min=0.0, soft_max=1.0)


# Custom Properties for SimpleRT renderer
class RenderSettings(bpy.types.PropertyGroup):
    samples: bpy.props.IntProperty(default=4, soft_min=0)
    recursion_depth: bpy.props.IntProperty(default=2, soft_min=0)
    ambient_color: bpy.props.FloatVectorProperty(
        default=(0.05, 0.05, 0.05), subtype="COLOR"
    )


# SimpleRT material panel
class SimpleRTMaterialPanel(bpy.types.Panel):
    bl_label = "SimpleRT Material"
    bl_idname = "OBJECT_PT_simpleRT_material"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"

    @classmethod
    def poll(cls, context):
        return context.scene.render.engine == "simple_RT"

    def draw(self, context):
        mat = context.object.simpleRT_material

        split = self.layout.split(factor=0.4)
        col_1 = split.column()
        col_2 = split.column()
        col_1.alignment = "RIGHT"

        col_1.label(text="Diffuse Color")
        col_2.prop(mat, "diffuse_color", text="")
        col_1.label(text="Specular Color")
        col_2.prop(mat, "specular_color", text="")
        col_1.label(text="Specular Hardness")
        col_2.prop(mat, "specular_hardness", text="")
        col_1.label(text="Fresnel")
        col_2.prop(mat, "use_fresnel", text="")

        col_1.label(text="Reflectivity")
        row = col_2.row()
        row.prop(mat, "mirror_reflectivity", text="")
        row.active = not mat.use_fresnel
        col_1.label(text="IOR")
        col_2.prop(mat, "ior", text="")

        col_1.label(text="transmission")
        col_2.prop(mat, "transmission", text="")


# SimpleRT light panel
class SimpleRTLightPanel(bpy.types.Panel):
    bl_label = "SimpleRT Light"
    bl_idname = "OBJECT_DATA_PT_simpleRT_light"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        return context.scene.render.engine == "simple_RT" and context.light

    def draw(self, context):
        layout = self.layout

        light = context.light

        layout.row().prop(light, "type", expand=True)
        layout.use_property_split = True

        col = layout.column()

        col.prop(light, "color")
        col.prop(light, "energy")
        col.separator()

        if light.type in {"POINT", "SPOT"}:
            col.prop(light, "shadow_soft_size", text="Radius")
        elif light.type == "SUN":
            col.prop(light, "angle")
        elif light.type == "AREA":
            col.prop(light, "shape", text="Shape")
            sub = col.column(align=True)

            if light.shape in {"SQUARE", "DISK"}:
                sub.prop(light, "size")
            elif light.shape in {"RECTANGLE", "ELLIPSE"}:
                sub.prop(light, "size", text="Size X")
                sub.prop(light, "size_y", text="Y")


# SimpleRT camera panel
class SimpleRTCameraPanel(bpy.types.Panel):
    bl_label = "SimpleRT Camera"
    bl_idname = "OBJECT_DATA_PT_simpleRT_camera"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        return context.scene.render.engine == "simple_RT" and context.camera

    def draw(self, context):
        cam = context.camera

        split = self.layout.split(factor=0.4)
        col_1 = split.column()
        col_2 = split.column()
        col_1.alignment = "RIGHT"

        col_1.label(text="Focal Length")
        col_1.label(text="Sensor Fit")
        col_1.label(text="Size")
        col_2.prop(cam, "lens", text="")
        col_2.prop(cam, "sensor_fit", text="")
        col_2.prop(cam, "sensor_width", text="")


# SimpleRT output panel
class SimpleRTDimensionsPanel(bpy.types.Panel):
    bl_label = "SimpleRT Dimensions"
    bl_idname = "OUTPUT_PT_simpleRT_dimension"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "output"

    @classmethod
    def poll(cls, context):
        return context.scene.render.engine == "simple_RT"

    def draw(self, context):
        rd = context.scene.render

        split = self.layout.split(factor=0.4)
        col_1 = split.column()
        col_2 = split.column(align=True)
        col_1.alignment = "RIGHT"

        col_1.label(text="Resolution X")
        col_1.label(text="Y")
        col_1.label(text="%")
        col_2.prop(rd, "resolution_x", text="")
        col_2.prop(rd, "resolution_y", text="")
        col_2.prop(rd, "resolution_percentage", text="")


# SimpleRT render settings panel
class SimpleRTRenderPanel(bpy.types.Panel):
    bl_label = "SimpleRT Render Settings"
    bl_idname = "RENDER_PT_simpleRT_render"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"

    @classmethod
    def poll(cls, context):
        return context.scene.render.engine == "simple_RT"

    def draw(self, context):
        sc = context.scene.simpleRT

        split = self.layout.split(factor=0.4)
        col_1 = split.column()
        col_2 = split.column()
        col_1.alignment = "RIGHT"

        col_1.label(text="samples")
        col_1.label(text="depth")
        col_1.label(text="ambient")
        col_2.prop(sc, "samples", text="")
        col_2.prop(sc, "recursion_depth", text="")
        col_2.prop(sc, "ambient_color", text="")


def register():
    # register custom properties
    bpy.utils.register_class(ObjectSettings)
    bpy.utils.register_class(RenderSettings)
    # register panels
    if not bpy.app.background:
        bpy.utils.register_class(SimpleRTMaterialPanel)
        bpy.utils.register_class(SimpleRTLightPanel)
        bpy.utils.register_class(SimpleRTCameraPanel)
        bpy.utils.register_class(SimpleRTDimensionsPanel)
        bpy.utils.register_class(SimpleRTRenderPanel)
    # add custom properties to existing types
    bpy.types.Scene.simpleRT = bpy.props.PointerProperty(type=RenderSettings)
    bpy.types.Object.simpleRT_material = bpy.props.PointerProperty(type=ObjectSettings)


def unregister():
    # unregister custom properties
    bpy.utils.unregister_class(ObjectSettings)
    bpy.utils.unregister_class(RenderSettings)
    # unregister panels
    bpy.utils.unregister_class(SimpleRTMaterialPanel)
    bpy.utils.unregister_class(SimpleRTLightPanel)
    bpy.utils.unregister_class(SimpleRTCameraPanel)
    bpy.utils.unregister_class(SimpleRTDimensionsPanel)
    bpy.utils.unregister_class(SimpleRTRenderPanel)


if __name__ == "__main__":
    register()
