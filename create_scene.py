import os, re
from random import randrange, gauss
from subprocess import call
from pymel.core import *
# from mg_utils import *

import pdb

def get_absolute_file_paths(folder, substring=''):
  file_names = []
  if (substring == ''):
    file_names = [os.path.join(folder, file_name) for file_name in os.listdir(folder) if os.path.isfile(os.path.join(folder, file_name))]
  else:
    file_names = [os.path.join(folder, file_name) \
      for file_name in os.listdir(folder) \
      if os.path.isfile(os.path.join(folder, file_name)) and \
      (re.search(substring, file_name) is not None)]
  
  return file_names

def separate_file_names(absolute_paths, delimiter='\\'):
  file_names = [get_image_name(absolute_path) for absolute_path in absolute_paths]
  return file_names

def get_image_name(absolute_path, delimiter='\\'):
  return absolute_path.split(delimiter)[-1].split('_shad')[0].lower()

def connect_object_to_shader(obj, shader):
  connectAttr(obj.getShape().instObjGroups[0], shaders_groups[shader+'SG'].dagSetMembers[1], f=1)

                
def disconnect_object_from_shader(obj, shader):
  disconnectAttr(obj.getShape().instObjGroups[0], shaders_groups[shader+'SG'].dagSetMembers[1])


def render_scene(out_im, scene_path):
  # save scene and render
  saveAs(scene_path, f=1)
  call("render -r mr -cam renderCam -im %s -v 0 %s" %(out_im, scene_path))


def cast_shadow(is_cast):
  occluder[0].getShape().setAttr('castsShadows', is_cast)
  occluder[0].getShape().setAttr('doubleSided', is_cast)

	
def setup_render_camera(translateY=10.0, rotateX=-90.0):
  renderCam = nt.Camera()
  renderCamParent = renderCam.getParent()
  renderCamParent.rename('renderCam')
  renderCamParent.translateY.set(translateY)
  renderCamParent.rotateX.set(rotateX)
  connectAttr(SCENE.mia_physicalsky1.message, renderCam.miEnvironmentShader)
  return renderCam

  
def setup_ground_plane(scale=50.0, slopeMin=-45, slopeMax=45):
  groundPlane = polyPlane(name='groundPlane')
  groundPlane[0].scaleX.set(scale)
  groundPlane[0].scaleZ.set(scale)
  groundPlane[0].rotateX.set(randrange(slopeMin, slopeMax))
  groundPlane[0].rotateZ.set(randrange(slopeMin, slopeMax))
  return groundPlane
	
  
def setup_occluder(height=10.0, scale=5.0):
  occluder = polyPlane(name='occluder')
  occluder[0].translateY.set(height)
  occluder[0].scaleX.set(scale)
  occluder[0].scaleZ.set(scale)
  occluder[0].setAttr('primaryVisibility', False)
  return occluder

  
def setup_area_light(light_name, height=30.0):
  light = nt.AreaLight(name = light_name)
  lightParent = light.getParent()
  # set light position
  lightParent.translateY.set(height)
  lightParent.rotateX.set(-90.0)	# point down

  # set light attributes
  light.setAttr('decayRate', 2)	# quadratic decay
  light.setAttr('intensity', 400)
  light.setAttr('useRayTraceShadows', True)
  light.setAttr('shadowRays', 100)
  light.setAttr('areaLight', True)
  light.setAttr('areaHiSamples', 50)
  # make sure the light illuminates everything
  connectAttr(light.instObjGroups[0], SCENE.defaultLightSet.dagSetMembers[0])
  return light

def setup_ambient_light(light_name):
  light = nt.AmbientLight(name=light_name)
  light.setAttr('intensity', 0.1)
  light.setAttr('ambientShade', 0.0)

def strip_file_extension(file_names):
  return [fname.split('.')[0] for fname in file_names]

  
current_folder = os.path.dirname(os.path.abspath(__file__))
base_path = os.path.join(current_folder, 'base_white.mb')
scene_path = os.path.join(current_folder, 'scene.mb')

# open base file if exists, otherwise create a new one
if os.path.exists(base_path):
  f = openFile(base_path, f=1)
else:
  f = newFile(f=1)

# shaders and shading groups
shaders_groups = {}

# get absolute paths to countour files
contour_folder = os.path.join(current_folder, 'contours')
contour_files = get_absolute_file_paths(contour_folder)
# get contour names
contour_names = separate_file_names(contour_files)
contour_names = strip_file_extension(contour_names)

# get absolute paths to texture files
texture_folder = os.path.join(current_folder, 'textures')
texture_files = get_absolute_file_paths(texture_folder)
# get texture names
texture_names = separate_file_names(texture_files)
texture_names = strip_file_extension(texture_names)

for contour in zip(contour_names, contour_files):
  shader, shading_group = createSurfaceShader('lambert', 'c'+contour[0])
  shaders_groups[contour[0] + 'Sh'] = shader
  shaders_groups[contour[0] + 'SG'] = shading_group
  shaders_groups[contour[0] + 'SN'] = shadingNode('file', asTexture=True, name=contour[0]+'_file')

  shaders_groups[contour[0] + 'Sh'].setAttr('shadowAttenuation', 0)
  shaders_groups[contour[0] + 'SN'].setAttr('fileTextureName', contour[1])
  shaders_groups[contour[0] + 'SN'].setAttr('alphaIsLuminance', 1)
  connectAttr(shaders_groups[contour[0] + 'SN'].outColor, shader.transparency)
	
for tex in zip(texture_names, texture_files):
  shader, shading_group = createSurfaceShader('lambert', tex[0])
  shaders_groups[tex[0] + 'Sh'] = shader
  shaders_groups[tex[0] + 'SG'] = shading_group
  shaders_groups[tex[0] + 'SN'] = shadingNode('file', asTexture=True, name=tex[0]+'_file')

  shaders_groups[tex[0] + 'SN'].setAttr('fileTextureName', tex[1])

  connectAttr(shaders_groups[tex[0] + 'SN'].outColor, shader.color)

# setup scene geometry
renderCam = setup_render_camera()
renderCamTransform = renderCam.getParent()
groundPlane = setup_ground_plane()
occluder = setup_occluder()
light1 = setup_area_light('light1')
light1Transform = light1.getParent()

# setup ambient light
light2 = setup_ambient_light('light2')

SCENE.mia_physicalsky1.setAttr('multiplier', 0.1);

# disconnect groundPlaneShape from default shader
dest = connectionInfo(groundPlane[0].getShape().instObjGroups[0], dfs=True)[0]
dsmn = re.search(r'([0-9])', dest).groups(0)[0];
disconnectAttr(groundPlane[0].getShape().instObjGroups[0], PyNode(dest.split('.')[0]).dagSetMembers[int(dsmn)])
disconnectAttr(occluder[0].getShape().instObjGroups[0], PyNode(dest.split('.')[0]).dagSetMembers[int(dsmn)])			   

n_images = 1000;

# variability
camera_height = [35.0, 5.0]
plane_angle = [0.0, 5.0]
occluder_scale = [15.0, 5.0]
occluder_twist = 180.0
light_angle_x = [-90.0, 5.0]
light_angle_z = [0.0, 5.0]
light_size = [4.0, 1.0]

count = 0
for i in range(n_images):
  # randomize render camera's height
  renderCamTransform.translateY.set(gauss(camera_height[0], camera_height[1]))
  # rangomize occluder size
  occluder[0].scaleX.set(gauss(occluder_scale[0], occluder_scale[1]))
  occluder[0].scaleZ.set(gauss(occluder_scale[0], occluder_scale[1]))
  # randomize receiving plane angle
  groundPlane[0].rotateX.set(gauss(plane_angle[0], plane_angle[1]))
  groundPlane[0].rotateZ.set(gauss(plane_angle[0], plane_angle[1]))
  # randomize occluding plane angle
  occluder[0].rotateX.set(gauss(plane_angle[0], plane_angle[1]))
  occluder[0].rotateY.set(gauss(0.0, occluder_twist))
  occluder[0].rotateZ.set(gauss(plane_angle[0], plane_angle[1]))
  # randomize light rotation and scaling
  light1Transform.rotateX.set(gauss(light_angle_x[0], light_angle_x[1]))
  light1Transform.rotateZ.set(gauss(light_angle_z[0], light_angle_z[1]))
  light1Transform.scaleX.set(gauss(light_size[0], light_size[1]));
  light1Transform.scaleY.set(gauss(light_size[0], light_size[1]));
  light1Transform.scaleZ.set(gauss(light_size[0], light_size[1]));
  # randomize light type
  light1.setAttr('areaType', randrange(0,3)) 

  # get random texture and contour names
  texture_name = texture_names[randrange(len(texture_names))]
  contour_name = contour_names[randrange(len(contour_names))]

  # set output image name
  out_im = os.path.join(current_folder, 'output', contour_name + '_' + texture_name)

  # connect chosen shaders, render images and disconnect
  connect_object_to_shader(groundPlane[0], texture_name)
  connect_object_to_shader(occluder[0], contour_name)

    # render shadow image
  cast_shadow(True)
  render_scene('%s_shad'%(out_im), scene_path)
  # render_scene('%s_shad_%i'%(out_im, count), scene_path)
  # render_scene(out_im+'_shad', scene_path)

  # render noshadow image
  cast_shadow(False)
  render_scene('%s_noshad'%(out_im), scene_path)
  # render_scene('%s_noshad_%i'%(out_im, count), scene_path)

  disconnect_object_from_shader(groundPlane[0], texture_name)
  disconnect_object_from_shader(occluder[0], contour_name)
  
  count += 1