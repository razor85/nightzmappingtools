import bpy
import bmesh
import ctypes
import math
import mathutils
import os
import pathlib
import gpu
import sys
import socket
from socket import ntohl
from socket import ntohs
from bpy import *
from math import *
from mathutils import Vector
from pathlib import Path

from bpy.app.handlers import persistent

bl_info = {
    "name": "Export generic game map data (.json)",
    "category": "Import-Export",
}

# Hold BMesh for each mesh.
globalMeshes = {}

class ExportMap(bpy.types.Operator):
    """Export selected objects to generic map format in json"""
    bl_idname = "export.to_generic_json_map"
    bl_label = "Export Generic Map (.json)"
    filepath = bpy.props.StringProperty(subtype='FILE_PATH')
        
    @classmethod
    def poll(cls, context):
        return bpy.context.selected_objects is not None

    def getFaces(self):
        vertexCount = 0
        facesData = []
        faceCount = 0
        
        selObjects = bpy.context.selected_objects
        for obj in selObjects:
            if obj.type != 'MESH':
                continue
                
            objNumVertices = 0
            objMesh = bmesh.new()
            objMesh.from_mesh(obj.data)
            objMesh.faces.ensure_lookup_table()
            
            if objMesh.faces.layers.int.get("FaceFlags") is None:
              objMesh.faces.layers.int.new("FaceFlags")
              
            flagsLayer = objMesh.faces.layers.int.get("FaceFlags")

            print("Writing obj faces (with {} vertices) starting at vertex index {}".format(len(obj.data.vertices), vertexCount))
            for poly in objMesh.faces:
                indices = []
                if len(poly.loops) == 3:
                  indices = [obj.data.loops[loop.index].vertex_index for loop in poly.loops[0:3]]
                elif len(poly.loops) == 4:
                  indices = [obj.data.loops[loop.index].vertex_index for loop in poly.loops[0:4]]
                
                materialIndex = poly.material_index
                assert materialIndex != None, 'Object must have a material'
                material = obj.data.materials[materialIndex]             
                
                faceData = "{ "
                faceData += "\"indices\" : [ {} ],\n".format(", ".join(str(x + vertexCount) for x in indices))
                faceData += "\"material\" : \"{}\"\n".format(material.name)
                faceData += "}"
                
                facesData.append(faceData)
                faceCount += 1
            
            # Add vertex count of active mesh to increase indices on next object.
            vertexCount += len(obj.data.vertices)
            
        return faceCount, ", ".join(facesData)
            
    def getMaterials(self):
        materials = []
        materialCount = 0
        
        for matName in self.materialDict:
            material = self.materialDict[ matName ]
            texturePath = ""
            
            texSlot = material.texture_slots[0]
            texture = getattr(texSlot, 'texture', None)
            if texSlot != None and texture != None and hasattr(texture, 'image'):
                textureImage = texture.image
                if textureImage.filepath != None:
                    tmpPath = pathlib.Path(textureImage.filepath)
                    texturePath = str(tmpPath).replace("\\", "\\\\")
                    
            matString = "\"name\" : \"{}\", \"texture\" : \"{}\"".format(matName, texturePath)
            materials.append("{" + matString + " } ")
            materialCount += 1
            
        return materialCount, ", ".join(materials)

    def getVertexData(self):
        vertexData = []
        vertexCount = 0
        
        selObjects = bpy.context.selected_objects
        for obj in selObjects:
            if obj.type != 'MESH':
                continue
                
            objMesh = bmesh.new()
            objMesh.from_mesh(obj.data)
            objMesh.verts.ensure_lookup_table()
            wsMatrix = obj.matrix_world
            for v in objMesh.verts:
                transformedVertex = wsMatrix * Vector((v.co[0], v.co[1], v.co[2], 1.0))
                vertexData.append( transformedVertex[0])
                vertexData.append(-transformedVertex[1])
                vertexData.append( transformedVertex[2])
                vertexCount += 1
                
        return vertexCount, ", ".join(str(x) for x in vertexData)

    def extractMaterialsUsed(self):
        selObjects = bpy.context.selected_objects
        for obj in selObjects:
            if obj.type != 'MESH':
                continue
                
            objData = obj.data

            # Extract pixels from UV.
            assert objData.uv_layers.active != None, 'Object must have a UV channel'
            for poly in objData.polygons:
              matIndex = poly.material_index
              assert matIndex != None, 'Object must have a material'

              material = objData.materials[matIndex]
              if material.name not in self.materialDict:
                self.materialDict[ material.name ] = material
                print("Registered used material \"{}\"".format(material.name))

    def execute(self, context):
        print("Saving generic map to '{}'...".format(self.filepath))
        self.materialDict = {}
                
        # Traverse scene and update meshes.
        selObjects = bpy.context.selected_objects
        for obj in selObjects:
            if obj.type != 'MESH':
                continue
                
            objMesh = obj.data
            objMesh.update()
            objMesh.calc_tangents()
            for f in objMesh.polygons:
                assert len(f.vertices) == 3 or len(f.vertices) == 4, 'Only triangles and quads are supported'
        
        # Register all materials used by selection.
        self.extractMaterialsUsed()
        
        filePath = Path(self.filepath)
        with filePath.open("w") as filePtr:
            vertexCount, vertexData = self.getVertexData()
            faceCount, faceData = self.getFaces()
            materialCount, materialData = self.getMaterials()
            
            # print("Vertex Data:\n {} \n\n".format(vertexData))
            # print("Face Data:\n {} \n\n".format(faceData))
            # print("Material Data:\n {} \n\n".format(materialData))
            
            filePtr.write("{\n")
            filePtr.write("  \"numFaces\" : {},\n".format(faceCount))
            filePtr.write("  \"numVertices\" : {},\n".format(vertexCount))
            filePtr.write("  \"numMaterials\" : {},\n".format(materialCount))
            filePtr.write("  \"materials\" : [ {} ],\n".format(materialData))
            filePtr.write("  \"vertices\" : [ {} ],\n".format(vertexData))
            filePtr.write("  \"faces\" : [ {} ]\n".format(faceData))
            filePtr.write("}\n")
            
            print("Exported {} vertices, {} faces and {} materials".format(vertexCount, faceCount, materialCount))

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


# Only needed if you want to add into a dynamic menu
def menu_func(self, context):
    self.layout.operator_context = 'INVOKE_DEFAULT'
    self.layout.operator(ExportMap.bl_idname,
                         text="Export to Generic Map JSON")

def setDithering(self, context):
    editObject = context.edit_object
    bm = globalMeshes.setdefault(editObject.name, 
                                 bmesh.from_edit_mesh(editObject.data))

    for face in bm.faces:
      if face.select == False:
        continue

      layer = bm.faces.layers.int.get("FaceFlags")
      if bpy.context.window_manager.useDithering:
        face[layer] |= FLAG_DITHERING
      else:
        face[layer] &= ~FLAG_DITHERING

    return None

def setTransparency(self, context):
    editObject = context.edit_object
    bm = globalMeshes.setdefault(editObject.name, 
                                 bmesh.from_edit_mesh(editObject.data))

    for face in bm.faces:
      if face.select == False:
        continue

      layer = bm.faces.layers.int.get("FaceFlags")
      if bpy.context.window_manager.useTransparency:
        face[layer] |= FLAG_TRANSPARENCY
      else:
        face[layer] &= ~FLAG_TRANSPARENCY

    return None

def setIgnoreFaceSize(self, context):
    editObject = context.edit_object
    bm = globalMeshes.setdefault(editObject.name, 
                                 bmesh.from_edit_mesh(editObject.data))

    for face in bm.faces:
      if face.select == False:
        continue

      layer = bm.faces.layers.int.get("FaceFlags")
      if bpy.context.window_manager.ignoreFaceSize:
        face[layer] |= FLAG_IGNORE_FACE_SIZE
      else:
        face[layer] &= ~FLAG_IGNORE_FACE_SIZE

    return None

# Store intermediate values for face flags.
bpy.types.WindowManager.useDithering = bpy.props.BoolProperty(name="Use Dithering", 
                                                              update=setDithering)
bpy.types.WindowManager.useTransparency = bpy.props.BoolProperty(name="Use Transparency", 
                                                                 update=setTransparency)
bpy.types.WindowManager.ignoreFaceSize = bpy.props.BoolProperty(name="Ignore Face Size", 
                                                                update=setIgnoreFaceSize)

# Update window manager values
def updateWMValues(bm):
  bm.faces.ensure_lookup_table()
  if bm.faces.layers.int.get("FaceFlags") is None:
    bm.faces.layers.int.new("FaceFlags")

  activeFaces = getActiveFaces(bm)
  if len(activeFaces) > 0:
    face = activeFaces[ 0 ]
    layer = bm.faces.layers.int.get("FaceFlags")
    bpy.context.window_manager.useDithering = ((face[layer] & FLAG_DITHERING) != 0)
    bpy.context.window_manager.useTransparency = ((face[layer] & FLAG_TRANSPARENCY) != 0)
    bpy.context.window_manager.ignoreFaceSize = ((face[layer] & FLAG_IGNORE_FACE_SIZE) != 0)

  return None

#scene update handler
@persistent
def editObjectChangeHandler(scene):
    obj = scene.objects.active
    if obj is None:
        return None

    # add one instance of edit bmesh to global dic
    if obj.mode == 'EDIT' and obj.type == 'MESH':
        bm = globalMeshes.setdefault(obj.name, bmesh.from_edit_mesh(obj.data))
        updateWMValues(bm)
        return None

    globalMeshes.clear()
    return None


def getActiveFaces(obj):
  faces = []
  for face in obj.faces:
    if face.select:
      faces.append(face)

  return faces

class MapEditPanel(bpy.types.Panel):
  bl_label = "JSON Map Exporter"
  bl_region_type = "UI"
  bl_space_type = "VIEW_3D"

  @classmethod
  def poll(cls, context):
    # Only allow in edit mode for a selected mesh.
    return context.mode == "EDIT_MESH" and context.object is not None and context.object.type == "MESH"

  def draw(self, context):
    selectedObject = context.object
    bm = globalMeshes.setdefault(selectedObject.name, 
                                 bmesh.from_edit_mesh(selectedObject.data))

    activeFaces = getActiveFaces(bm)
    if len(activeFaces) > 1:
      self.layout.label("Multiple faces selected.")

    self.layout.prop(context.window_manager, "useDithering", text="Use Dithering")
    self.layout.prop(context.window_manager, "useTransparency", text="Use Transparency")
    self.layout.prop(context.window_manager, "ignoreFaceSize", text="Ignore Face Size")
    

def register():
  bpy.utils.register_class(ExportMap)
  bpy.utils.register_class(MapEditPanel)
  bpy.types.INFO_MT_file_export.append(menu_func)

  # Face properties panel event handler.
  bpy.app.handlers.scene_update_post.clear()
  bpy.app.handlers.scene_update_post.append(editObjectChangeHandler)

def unregister():
  bpy.utils.unregister_class(ExportMap)
  bpy.utils.unregister_class(MapEditPanel)

  bpy.types.INFO_MT_file_export.remove(menu_func)
  bpy.app.handlers.scene_update_post.clear()


# This allows you to run the script directly from blenders text editor
# to test the addon without having to install it.
if __name__ == "__main__":
    register()

