bl_info = {
    "name": "simple_ray_tracer",
    "description": "Simple Ray-tracer for CS 148",
    "author": "CS148",
    "version": (0, 0, 2023),
    "blender": (3, 5, 1),
    "wiki_url": "http://web.stanford.edu/class/cs148/",
    "category": "Render",
}


import bpy
import numpy as np
from mathutils import Vector
from math import sqrt


def ray_cast(scene, origin, direction):
    """wrapper around Blender's Scene.ray_cast() API
    Parameters
    ----------
    scene ： bpy.types.Scene
        The Blender scene we will cast a ray in
    origin : Vector, float array of 3 items
        Origin of the ray
    direction : Vector, float array of 3 items
        Direction of the ray
    Returns
    -------
    has_hit : bool
        The result of the ray cast, i.e. if the ray hits anything in the scene
    hit_loc : Vector, float array of 3 items
        The hit location of this ray cast
    hit_norm : Vector, float array of 3 items
        The face normal at the ray cast hit location
    index : int
        The face index of the hit face of the hit object
        -1 when original data isn’t available
    hit_obj : bpy_types.Object
        The hit object
    matrix: Matrix, float 4 * 4
        The matrix_world of the hit object
    """
    return scene.ray_cast(scene.view_layers[0].depsgraph, origin, direction)


def RT_trace_ray(scene, ray_orig, ray_dir, lights, depth=0):

    color = np.zeros(3)

    """
    Step 0: Hit?
    """
    has_hit, hit_loc, hit_norm, _, hit_obj, _ = ray_cast(scene, ray_orig, ray_dir)

    if not has_hit:
        return color

    ray_inside_object = False

    """
    Convention - norm's dir 
    """
    if hit_norm.dot(ray_dir) > 0:
        hit_norm = -hit_norm
        ray_inside_object = True

    """
    Some info we will use later 
    """
    ambient_color = scene.simpleRT.ambient_color
    eps = 1e-3
    mat = hit_obj.simpleRT_material
    diffuse_color = Vector(mat.diffuse_color).xyz
    specular_color = Vector(mat.specular_color).xyz
    specular_hardness = mat.specular_hardness

    hit_by_light = False

    """
    Step 1: Shadow rays 
    """
    for light in lights:
        light_color = np.array(
            light.data.simpleRT_light.color * light.data.simpleRT_light.energy
        )

        has_light_hit, _, _, _, _, _ = ray_cast(
            scene, hit_loc + hit_norm * eps, (light.location - hit_loc).normalized()
        ) 

        if has_light_hit:
            continue 
        
        hit_by_light = True

        """
        Step 2.a: Blinn-Phong
        """

        """
        Diffuse color 
        """
        I = light_color / np.linalg.norm(light.location - hit_loc) ** 2 
        diffuse = I * hit_norm.dot((light.location - hit_loc).normalized()) * diffuse_color

        """
        Specular color 
        """
        H = ((light.location - hit_loc).normalized() + (-ray_dir)).normalized()
        specular = I * pow(H.dot(hit_norm), specular_hardness) * specular_color

        """
        Combine info 
        """
        color += diffuse
        color += specular

    """
    Step 2.b: Ambient
    """
    if not hit_by_light:
        color += ambient_color

    """
    Step 3.a: Recursion & Reflection 
    """
    #reflectivity = mat.mirror_reflectivity # Constant 
    
    """
    Step 3.b: Fresnel
    """
    n1 = 1.0
    n2 = mat.ior
    r0 = ((n1 - n2) / (n1 + n2)) ** 2
    reflectivity = r0 + (1 - r0) * ((1 + ray_dir.dot(hit_norm)) ** 5)

    # the recursion and reflection
    if depth > 0:
        ref_orig = hit_loc + hit_norm * eps
        ref_dir = ray_dir - 2 * hit_norm.dot(ray_dir) * hit_norm
        # recursive call for reflection and transmission
        reflection_color = RT_trace_ray(
            scene, ref_orig, ref_dir, lights, depth - 1
        )
        color += reflection_color * reflectivity # use Fresnel reflectivity

    return color

def RT_render_scene(scene, width, height, depth, buf):
    """Main function for rendering the scene
    Parameters
    ----------
    scene : bpy.types.Scene
        The scene that will be rendered
        It stores information about the camera, lights, objects, and material
    width : int
        Width of the rendered image
    height : int
        Height of the rendered image
    depth : int
        The recursion depth of raytracing
        i.e. the number that light bounces in the scene
    buf: numpy.ndarray
        the buffer that will be populated to store the calculated color
        for each pixel
    """

    # get all the lights from the scene
    scene_lights = [o for o in scene.objects if o.type == "LIGHT"]

    # get the location and orientation of the active camera
    cam_location = scene.camera.location
    cam_orientation = scene.camera.rotation_euler

    # get camera focal length
    focal_length = scene.camera.data.lens / scene.camera.data.sensor_width
    aspect_ratio = height / width

    # iterate through all the pixels, cast a ray for each pixel
    for y in range(height):
        # get screen space coordinate for y
        screen_y = ((y - (height / 2)) / height) * aspect_ratio
        for x in range(width):
            # get screen space coordinate for x
            screen_x = (x - (width / 2)) / width
            # calculate the ray direction
            ray_dir = Vector((screen_x, screen_y, -focal_length))
            ray_dir.rotate(cam_orientation)
            ray_dir = ray_dir.normalized()
            # populate the RGB component of the buffer with ray tracing result
            buf[y, x, 0:3] = RT_trace_ray(
                scene, cam_location, ray_dir, scene_lights, depth
            )
            # populate the alpha component of the buffer
            # to make the pixel not transparent
            buf[y, x, 3] = 1
        yield y
    return buf


# modified from https://docs.blender.org/api/current/bpy.types.RenderEngine.html
class SimpleRTRenderEngine(bpy.types.RenderEngine):
    # These three members are used by blender to set up the
    # RenderEngine; define its internal name, visible name and capabilities.
    bl_idname = "simple_RT"
    bl_label = "SimpleRT"
    bl_use_preview = False

    # Init is called whenever a new render engine instance is created. Multiple
    # instances may exist at the same time, for example for a viewport and final
    # render.
    def __init__(self):
        self.draw_data = None

    # When the render engine instance is destroy, this is called. Clean up any
    # render engine data here, for example stopping running render threads.
    def __del__(self):
        pass

    # This is the method called by Blender for both final renders (F12) and
    # small preview for materials, world and lights.
    def render(self, depsgraph):
        scene = depsgraph.scene
        scale = scene.render.resolution_percentage / 100.0
        self.size_x = int(scene.render.resolution_x * scale)
        self.size_y = int(scene.render.resolution_y * scale)

        if self.is_preview:
            pass
        else:
            self.render_scene(scene)

    def render_scene(self, scene):
        # create a buffer to store the calculated intensities
        # buffer is has four channels: Red, Green, Blue, and Alpha
        # default is set to (0, 0, 0, 0), which means black and fully transparent
        height, width = self.size_y, self.size_x
        buf = np.zeros((height, width, 4))

        result = self.begin_result(0, 0, self.size_x, self.size_y)
        layer = result.layers[0].passes["Combined"]

        # get the maximum ray tracing recursion depth
        depth = scene.simpleRT.recursion_depth

        # time the render
        import time
        from datetime import timedelta

        start_time = time.time()

        # start ray tracing
        update_cycle = int(10000 / width)
        for y in RT_render_scene(scene, width, height, depth, buf):

            # print render time info
            elapsed = int(time.time() - start_time)
            remain = int(elapsed / (y + 1) * (height - y - 1))
            print(
                f"rendering... Time {timedelta(seconds=elapsed)}"
                + f"| Remaining {timedelta(seconds=remain)}",
                end="\r",
            )

            # update Blender progress bar
            self.update_progress(y / height)

            # update render result
            # update too frequently will significantly slow down the rendering
            if y % update_cycle == 0 or y == height - 1:
                self.update_result(result)
                layer.rect = buf.reshape(-1, 4).tolist()

            # catch "ESC" event to cancel the render
            if self.test_break():
                break

        # tell Blender all pixels have been set and are final
        self.end_result(result)


def register():
    bpy.utils.register_class(SimpleRTRenderEngine)


def unregister():
    bpy.utils.unregister_class(SimpleRTRenderEngine)


if __name__ == "__main__":
    register()