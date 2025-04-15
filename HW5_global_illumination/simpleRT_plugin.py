#  simpleRT_plugin.py
#
#  Blender add-on for simpleRT render engine
#  a minimal ray tracing engine for CS148 HW5
#
#  Adding area light, sampling, and indirect illumination (GI)


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
from mathutils import Vector, Matrix
from math import sqrt, pi, cos, sin
import math, random

def ray_cast(scene, origin, direction):
    return scene.ray_cast(scene.view_layers[0].depsgraph, origin, direction)


def RT_trace_ray(scene, ray_orig, ray_dir, lights, depth=0):
    # First, we cast a ray into the scene using Blender's built-in function
    has_hit, hit_loc, hit_norm, _, hit_obj, _ = ray_cast(scene, ray_orig, ray_dir)
    # set initial color (black) for the pixel
    color = np.zeros(3)
    # if the ray hits nothing in the scene, return black
    if not has_hit:
        return color
    # small offset to prevent self-occlusion for secondary rays
    eps = 1e-3
    # fix normal direction
    ray_inside_object = False
    if hit_norm.dot(ray_dir) > 0:
        hit_norm = -hit_norm
        ray_inside_object = True

    # get the ambient color of the scene
    ambient_color = scene.simpleRT.ambient_color
    # get the material of the object we hit
    mat = hit_obj.simpleRT_material
    # extract properties from the material
    diffuse_color = Vector(mat.diffuse_color).xyz
    specular_color = Vector(mat.specular_color).xyz
    specular_hardness = mat.specular_hardness

    # set flag for light hit. Will later be used to apply ambient light
    no_light_hit = True

    # iterate through all the lights in the scene
    for light in lights:
        # get light color
        light_color = np.array(light.data.color * light.data.energy / 4 / pi)
        light_loc = light.location

        """one point sampling for area light"""
        if light.data.type == "AREA":
            # Sample a random point on the area light in its local space
            theta = np.random.uniform(0, 2 * np.pi)
            r = np.random.uniform(0, 1)
            x = sqrt(r) * cos(theta)
            y = sqrt(r) * sin(theta)
            z = 0
            sample_local = Vector((x, y, z)) * (light.data.size / 2)

            # Transform the sampled point into world space
            light_loc = light.matrix_world @ sample_local

            # Compute the light's emission normal in world space
            light_normal = Vector((0, 0, -1))
            light_normal.rotate(light.rotation_euler)
            
            # Now compute the cosine factor using the sampled light location.
            cos_theta = (hit_loc - light_loc).normalized().dot(light_normal)
            if cos_theta < 0:

                light_color = np.zeros(3)
            else:
                # print("cos_theta", cos_theta)
                light_color *= cos_theta
        """end of area light sampling"""
        
        # calculate vectors for shadow ray
        light_vec = light_loc - hit_loc
        light_dir = light_vec.normalized()
        new_orig = hit_loc + hit_norm * eps
        # cast shadow ray
        has_light_hit, light_hit_loc, _, _, _, _ = ray_cast(scene, new_orig, light_dir)
        if has_light_hit and (light_hit_loc - new_orig).length < light_vec.length:
            continue
        # Blinn-Phong diffuse
        I_light = light_color / light_vec.length_squared
        color += np.array(diffuse_color) * I_light * hit_norm.dot(light_dir)
        # Blinn-Phong specular
        half_vector = (light_dir - ray_dir).normalized()
        specular_reflection = hit_norm.dot(half_vector) ** specular_hardness
        color += np.array(specular_color) * I_light * specular_reflection
        # flag for ambient
        no_light_hit = False

    if depth > 0:
        # need to find the x axis and the y axis so that the z axis is the normal
        # init guess 
        x_axis = Vector((0, 0, 1)) # the first guess 
        if abs(hit_norm.dot(x_axis)) > 0.9:
            x_axis = Vector((0, 1, 0)) # if these two are too close, switch

        # compute the real x axis
        x_axis = x_axis - hit_norm * hit_norm.dot(x_axis)
        x_axis.normalize()
        # compute the real y axis
        y_axis = hit_norm.cross(x_axis)
        y_axis.normalize()

        r1 = random.random()  # uniform in [0,1]
        r2 = random.random()  # uniform in [0,1]
        
        # Let r1 = cos(theta), so theta = arccos(r1)
        # theta = math.acos(r1)
        # Let phi = 2π * r2
        phi = 2.0 * math.pi * r2

        sin_theta = math.sqrt(1 - r1 * r1)

        # x = sin_theta * math.cos(phi)
        # y = sin_theta * math.sin(phi)
        # z = r1  # z corresponds to cos(theta)

        local_dir = Vector((sin_theta * math.cos(phi), sin_theta * math.sin(phi), r1))
        transform = Matrix((x_axis, y_axis, hit_norm)).transposed()
        world_dir = transform @ local_dir
        world_dir.normalize()

        color += RT_trace_ray(
            scene, hit_loc + hit_norm * eps, world_dir, lights, depth - 1
        ) * diffuse_color * r1

    # ambient
    if no_light_hit:
        color += np.array(diffuse_color) * ambient_color

    # calculate reflectivity/fresnel
    reflectivity = mat.mirror_reflectivity
    if mat.use_fresnel:
        n2 = mat.ior
        r0 = ((1 - n2) / (1 + n2)) ** 2
        reflectivity = r0 + (1 - r0) * ((1 + ray_dir.dot(hit_norm)) ** 5)

    # recursive call for reflection and transmission
    if depth > 0:
        # reflection
        reflection_dir = (ray_dir - 2 * hit_norm * ray_dir.dot(hit_norm)).normalized()
        reflect_color = RT_trace_ray(
            scene, hit_loc + hit_norm * eps, reflection_dir, lights, depth - 1
        )
        color += reflectivity * reflect_color
        # transmission
        if mat.transmission > 0:
            if ray_inside_object:
                ior_ratio = mat.ior / 1
            else:
                ior_ratio = 1 / mat.ior
            under_sqrt = 1 - ior_ratio ** 2 * (1 - (ray_dir.dot(-hit_norm)) ** 2)
            if under_sqrt > 0:
                transmission_dir = ior_ratio * (
                    ray_dir - ray_dir.dot(hit_norm) * hit_norm
                ) - hit_norm * sqrt(under_sqrt)
                transmission_color = RT_trace_ray(
                    scene,
                    hit_loc - hit_norm * eps,
                    transmission_dir,
                    lights,
                    depth - 1,
                )
                color += (1 - reflectivity) * mat.transmission * transmission_color
    return color


# low-discrepancy sequence Van der Corput
def corput(n, base=2):
    q, denom = 0, 1
    while n:
        denom *= base
        n, remainder = divmod(n, base)
        q += remainder / denom
    return q - 0.5


def RT_render_scene(scene, width, height, depth, samples, buf):
    # get all lights from the scene
    scene_lights = [o for o in scene.objects if o.type == "LIGHT"]

    # get the location and orientation of the active camera
    cam_location = scene.camera.location
    cam_orientation = scene.camera.rotation_euler

    # get camera focal length
    focal_length = scene.camera.data.lens / scene.camera.data.sensor_width
    aspect_ratio = height / width

    # Compute pixel dimensions for low-discrepancy sampling:
    # dx is 1/width, and dy is computed as aspect_ratio/height.
    dx = 1.0 / width
    dy = aspect_ratio / height # aspect_ratio = width / height 

    corput_x = [corput(i, 2) * dx for i in range(samples)]
    corput_y = [corput(i, 3) * dy for i in range(samples)]

    sbuf = np.zeros((height, width, 3))
    # iterate on samples
    for s in range(samples):
        # iterate through all the pixels, cast a ray for each pixel
        for y in range(height):
            # get screen space coordinate for y
            screen_y = ((y - (height / 2)) / height) * aspect_ratio # + corput_y[s]
            for x in range(width):
                # get screen space coordinate for x
                screen_x = (x - (width / 2)) / width # + corput_x[s]

                ray_dir = Vector(
                    (screen_x + corput_x[s], screen_y + corput_y[s], -focal_length)
                )

                ray_dir.rotate(cam_orientation)
                ray_dir = ray_dir.normalized()

                # buf[y, x, 0:3] += RT_trace_ray( # [0 : 3] -> (r, g, b)
                #     scene, cam_location, ray_dir, scene_lights, depth
                # )

                color = RT_trace_ray(
                    scene, cam_location, ray_dir, scene_lights, depth
                )

                sbuf[y, x, :] += color 

                # update the pixel color in the buffer
                buf[y, x, 0:3] = sbuf[y, x, :] / (s + 1)

                # populate the alpha component of the buffer
                # to make the pixel not transparent
                buf[y, x, 3] = 1 # [3] -> alpha
            yield y + s * height
    
    # buf = sbuf[:, :, 0:3] / samples
    return buf


# modified from https://docs.blender.org/api/current/bpy.types.RenderEngine.html
class SimpleRTRenderEngine(bpy.types.RenderEngine):
    bl_idname = "simple_RT"
    bl_label = "SimpleRT"
    bl_use_preview = False

    def __init__(self):
        self.draw_data = None

    def __del__(self):
        pass

    def render(self, depsgraph):
        scene = depsgraph.scene
        scale = scene.render.resolution_percentage / 100.0
        self.size_x = int(scene.render.resolution_x * scale)
        self.size_y = int(scene.render.resolution_y * scale)

        # ----------
        self.samples = depsgraph.scene.simpleRT.samples # depsgraph.scene.simpleRT.samples
        # print(depsgraph.scene.simpleRT.samples)
        # ----------

        if self.is_preview:
            pass
        else:
            self.render_scene(scene)

    def render_scene(self, scene):
        height, width = self.size_y, self.size_x
        buf = np.zeros((height, width, 4))

        result = self.begin_result(0, 0, self.size_x, self.size_y)
        layer = result.layers[0].passes["Combined"]

        # get the maximum ray tracing recursion depth
        depth = scene.simpleRT.recursion_depth

        samples = self.samples
        total_height = samples * height

        # time the render
        import time
        from datetime import timedelta

        start_time = time.time()

        # start ray tracing
        update_cycle = int(10000 / width)
        for y in RT_render_scene(scene, width, height, depth, samples, buf):

            elapsed = int(time.time() - start_time)
            remain = int(elapsed / (y + 1) * (total_height - y - 1))
            status = (
                f"pass {y//height+1}/{samples} "
                + f"| Remaining {timedelta(seconds=remain)}"
            )
            self.update_stats("", status)
            print(status, end="\r")
            # update Blender progress bar
            self.update_progress(y / total_height)
            # update render result
            # update too frequently will significantly slow down the rendering
            if y % update_cycle == 0 or y == total_height - 1:
                self.update_result(result)
                layer.rect = buf.reshape(-1, 4).tolist()

            # catch "ESC" event to cancel the render
            if self.test_break():
                break

        # tell Blender all pixels have been set and are final
        self.end_result(result)


def register():
    bpy.utils.register_class(SimpleRTRenderEngine)
    # bpy.utils.register_class(SimpleRayTracer)


def unregister():
    # bpy.utils.unregister_class(SimpleRayTracer)
    bpy.utils.unregister_class(SimpleRTRenderEngine)


if __name__ == "__main__":
    register()