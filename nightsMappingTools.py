import bpy
import bpy.utils.previews
import bmesh
import os
from math import cos, sin, radians
from random import randint

# For custom icons.
icons_dict = bpy.utils.previews.new()

# When using as addon
#icons_dir = os.path.join(os.path.dirname(__file__), "icons")

# When using in the editor:
script_path = bpy.context.space_data.text.filepath
icons_dir = os.path.join(os.path.dirname(script_path), "icons")

# Keep track of created materials.
materials_dict = {}

# Load icons :)
iconFilenames = [f for f in os.listdir(icons_dir) if os.path.isfile(os.path.join(icons_dir, f))]
for filename in iconFilenames:
	icons_dict.load(os.path.splitext(filename)[0], os.path.join(icons_dir, filename), 'IMAGE')

def getIcon(name):
	return icons_dict[name].icon_id
	
def getSelectedTexture(op, context):
	browsers = [x for x in bpy.context.window.screen.areas if x.type == 'FILE_BROWSER']
	if len(browsers) == 0:
		op.report({"ERROR"}, "You must have a file browser window active")
	elif len(browsers) != 1:	
		op.report({"ERROR"}, "You must have exactly ONE file browser window active")
		
	selection = browsers[0].spaces[0].params
	return os.path.join(selection.directory, selection.filename)
    
def getSelectedObject(op, context):
	objs = bpy.context.selected_editable_objects
	if len(objs) != 1:
		activeObj = bpy.context.active_object
		if activeObj == None:
			op.report({"ERROR"}, "You must have a face selected inside an editable object")
		else:
			objs = [ activeObj ]
		
	return objs[0]
	
def doApplyBrowserTextureToFace(hasAlpha, op, context):
	textureFilename = getSelectedTexture(op, context)
	textureFile = os.path.split(textureFilename)[1]
	object = getSelectedObject(op, context)
	
	if len(object.data.uv_layers) == 0:
		bpy.ops.mesh.uv_texture_add()
	
	# Create a new material
	materialName = "FaceMaterial_{}".format(os.path.splitext(textureFile)[0])
	if materialName in materials_dict:
		newMaterial = materials_dict[ materialName ]
	else:
		newMaterial = bpy.data.materials.new(materialName)
		newMaterial.use_shadeless = True
		newMaterial.use_transparency = hasAlpha
		newMaterial.transparency_method = 'Z_TRANSPARENCY'
		newMaterial.alpha = 0
			
		newTextureName = "FaceTexture_{}".format(os.path.splitext(textureFile)[0])
		newTexture = bpy.data.textures.new(newTextureName, "IMAGE")
		newTexture.image = bpy.data.images.load(textureFilename)
			
		newMaterial.texture_slots.add()
		newMaterial.texture_slots[0].texture = newTexture
		newMaterial.texture_slots[0].use_map_alpha = hasAlpha
		newMaterial.texture_slots[0].alpha_factor = 1.0
		
		object.data.materials.append(newMaterial)
		materials_dict[ materialName ] = newMaterial
		
	newMaterialIndex = object.data.materials.keys().index(newMaterial.name)
	mesh = bmesh.from_edit_mesh(object.data)
	selectedFaces = [f for f in mesh.faces if f.select]
	if len(selectedFaces) == 0:	
		op.report({"ERROR"}, "You must have a face selected inside an editable object")
		
	# Deselect
	for f in mesh.faces:
		f.select = False
		
	# Create UV		
	for f in selectedFaces:
		f.select = True
		bpy.ops.uv.unwrap()
		bpy.ops.uv.reset()
			
		f.material_index = newMaterialIndex
		f.select = False
		
	# Reselect
	for f in selectedFaces:
		f.select = True	
		
	bmesh.update_edit_mesh(object.data)
	
	
def transformUV(function, op, context):
	print("Rotating uv...")
	
	object = getSelectedObject(op, context)
	
	mesh = bmesh.from_edit_mesh(object.data)
	uvRef = mesh.loops.layers.uv.active
	selectedFaces = [f for f in mesh.faces if f.select]
	if len(selectedFaces) == 0:	
		op.report({"ERROR"}, "You must have a face selected inside an editable object")
		
	for f in selectedFaces:
		for loop in f.loops:
			print("Coord {}".format(loop[uvRef].uv))
			loop[uvRef].uv = function(loop[uvRef].uv)
			print("Transformed Coord {}".format(loop[uvRef].uv))
			
	
	bmesh.update_edit_mesh(object.data)
	
def rotateBy(angle, point, anchor):
	cAngle = cos(radians(angle))
	sAngle = sin(radians(angle))
	
	x,y = point[0] - anchor[0], point[1] - anchor[1]
	return (x * cAngle - sAngle * y + anchor[0], 
			sAngle * x + cAngle * y + anchor[1])

centerAnchor = (0.5, 0.5)			
def doRotateUV(op, context):
	func = lambda uv: rotateBy(90, uv, centerAnchor)
	transformUV(func, op, context)
	
def doScaleUVHelper(uv, scale, anchor):
	x, y = uv[0] - anchor[0], uv[1] - anchor[1]
	x, y = x * scale[0] + anchor[0], y * scale[1] + anchor[1]
	return (x,y)
	
def doShrinkUV(op, context):
	func = lambda uv: doScaleUVHelper(uv, (1.1, 1.1), centerAnchor)
	transformUV(func, op, context)

def doShrinkHorizontalUV(op, context):
	func = lambda uv: doScaleUVHelper(uv, (1.1, 1.0), centerAnchor)
	transformUV(func, op, context)
	
def doShrinkVerticalUV(op, context):
	func = lambda uv: doScaleUVHelper(uv, (1.0, 1.1), centerAnchor)
	transformUV(func, op, context)
	
def doExpandUV(op, context):
	func = lambda uv: doScaleUVHelper(uv, (0.9, 0.9), centerAnchor)
	transformUV(func, op, context)
	
def doExpandHorizontalUV(op, context):
	func = lambda uv: doScaleUVHelper(uv, (0.9, 1.0), centerAnchor)
	transformUV(func, op, context)
	
def doExpandVerticalUV(op, context):
	func = lambda uv: doScaleUVHelper(uv, (1.0, 0.9), centerAnchor)
	transformUV(func, op, context)

def doMoveUVHelper(uv, move):
	x, y = uv[0] + move[0], uv[1] + move[1]
	return (x,y)
	
def doMoveUV_Up(op, context):
	func = lambda uv: doMoveUVHelper(uv, (0, 0.1))
	transformUV(func, op, context)
	
def doMoveUV_Down(op, context):
	func = lambda uv: doMoveUVHelper(uv, (0, -0.1))
	transformUV(func, op, context)
	
def doMoveUV_Left(op, context):
	func = lambda uv: doMoveUVHelper(uv, (-0.1, 0))
	transformUV(func, op, context)

def doMoveUV_Right(op, context):
	func = lambda uv: doMoveUVHelper(uv, (0.1, 0))
	transformUV(func, op, context)
	
class ApplyTextureFaceOperator(bpy.types.Operator):
	"""Tooltip"""
	bl_idname = "object.apply_texture_face_operator"
	bl_label = "Selected Texture to Face"

	@classmethod
	def poll(cls, context):
		return context.active_object is not None

	def execute(self, context):
		doApplyBrowserTextureToFace(False, self, context)
		return {'FINISHED'}
		
class ApplyTextureFaceAlphaOperator(bpy.types.Operator):
	"""Tooltip"""
	bl_idname = "object.apply_texture_face_alpha_operator"
	bl_label = "Selected Texture to Face Alpha"

	@classmethod
	def poll(cls, context):
		return context.active_object is not None

	def execute(self, context):
		doApplyBrowserTextureToFace(True, self, context)
		return {'FINISHED'}
		
class RotateUVOperator(bpy.types.Operator):
	"""Rotate UV"""
	bl_idname = "object.rotate_uv_operator"
	bl_label = "Rotate UV 90º"

	@classmethod
	def poll(cls, context):
		return context.active_object is not None

	def execute(self, context):
		doRotateUV(self, context)
		return {'FINISHED'}		
		
class ShrinkUVOperator(bpy.types.Operator):
	"""Shrink UV"""
	bl_idname = "object.shrink_uv_operator"
	bl_label = "Shrink UV"

	@classmethod
	def poll(cls, context):
		return context.active_object is not None

	def execute(self, context):
		doShrinkUV(self, context)
		return {'FINISHED'}	
		
class ShrinkUVHorizontalOperator(bpy.types.Operator):
	"""Shrink UV Horizontally"""
	bl_idname = "object.shrink_uv_horizontal_operator"
	bl_label = "Shrink UV Horizontally"

	@classmethod
	def poll(cls, context):
		return context.active_object is not None

	def execute(self, context):
		doShrinkHorizontalUV(self, context)
		return {'FINISHED'}	
		
class ShrinkUVVerticalOperator(bpy.types.Operator):
	"""Shrink UV Vertically"""
	bl_idname = "object.shrink_uv_vertical_operator"
	bl_label = "Shrink UV Vertically"

	@classmethod
	def poll(cls, context):
		return context.active_object is not None

	def execute(self, context):
		doShrinkVerticalUV(self, context)
		return {'FINISHED'}	
		
class ExpandUVOperator(bpy.types.Operator):
	"""Expand UV"""
	bl_idname = "object.expand_uv_operator"
	bl_label = "Expand UV"

	@classmethod
	def poll(cls, context):
		return context.active_object is not None

	def execute(self, context):
		doExpandUV(self, context)
		return {'FINISHED'}	

class MoveUVUpOperator(bpy.types.Operator):
	"""Expand UV"""
	bl_idname = "object.move_uv_up_operator"
	bl_label = "Move UV Up"

	@classmethod
	def poll(cls, context):
		return context.active_object is not None

	def execute(self, context):
		doMoveUV_Up(self, context)
		return {'FINISHED'}	
		
class MoveUVDownOperator(bpy.types.Operator):
	"""Expand UV"""
	bl_idname = "object.move_uv_down_operator"
	bl_label = "Move UV Down"

	@classmethod
	def poll(cls, context):
		return context.active_object is not None

	def execute(self, context):
		doMoveUV_Down(self, context)
		return {'FINISHED'}	
		
class MoveUVLeftOperator(bpy.types.Operator):
	"""Expand UV"""
	bl_idname = "object.move_uv_left_operator"
	bl_label = "Move UV Left"

	@classmethod
	def poll(cls, context):
		return context.active_object is not None

	def execute(self, context):
		doMoveUV_Left(self, context)
		return {'FINISHED'}	
		
class MoveUVRightOperator(bpy.types.Operator):
	"""Expand UV"""
	bl_idname = "object.move_uv_right_operator"
	bl_label = "Move UV Right"

	@classmethod
	def poll(cls, context):
		return context.active_object is not None

	def execute(self, context):
		doMoveUV_Right(self, context)
		return {'FINISHED'}	
		
class ExpandUVHorizontalOperator(bpy.types.Operator):
	"""Expand UV Horizontally"""
	bl_idname = "object.expand_uv_horizontal_operator"
	bl_label = "Expand UV Horizontally"

	@classmethod
	def poll(cls, context):
		return context.active_object is not None

	def execute(self, context):
		doExpandHorizontalUV(self, context)
		return {'FINISHED'}	
		
class ExpandUVVerticalOperator(bpy.types.Operator):
	"""Expand UV Vertically"""
	bl_idname = "object.expand_uv_vertical_operator"
	bl_label = "Expand UV Vertically"

	@classmethod
	def poll(cls, context):
		return context.active_object is not None

	def execute(self, context):
		doExpandVerticalUV(self, context)
		return {'FINISHED'}	
		
class NightzMapperToolsPanel(bpy.types.Panel):
	"""Creates a Panel in the Object properties window"""
	bl_label = "Nightz Mapper Tools"
	bl_idname = "OBJECT_PT_hello"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_context = "object"

	def draw(self, context):
		layout = self.layout

		obj = context.object

		row = layout.row()
		row.label(text="Active object is: " + obj.name)
		
		row = layout.row()
		row.operator("object.apply_texture_face_operator")
		row = layout.row()
		row.operator("object.apply_texture_face_alpha_operator")
		
		row = layout.row()
		row.operator("object.rotate_uv_operator", text="Rotate UV", icon_value=getIcon("arrow_rotate_clockwise"))
				
		row = layout.row()
		row.operator("object.shrink_uv_operator", text="", icon_value=getIcon("arrow_in"))
		row.operator("object.shrink_uv_horizontal_operator", text="", icon_value=getIcon("shrink_horizontal"))
		row.operator("object.expand_uv_horizontal_operator", text="", icon_value=getIcon("arrow_grow_horizontal"))
		row.operator("object.move_uv_left_operator", text="", icon_value=getIcon("arrow_left"))
		row.operator("object.move_uv_right_operator", text="", icon_value=getIcon("arrow_right"))
		
		row = layout.row()
		row.operator("object.expand_uv_operator", text="", icon_value=getIcon("arrow_out"))
		row.operator("object.shrink_uv_vertical_operator", text="", icon_value=getIcon("shrink_vertical"))
		row.operator("object.expand_uv_vertical_operator", text="", icon_value=getIcon("arrow_grow_vertical"))
		row.operator("object.move_uv_up_operator", text="", icon_value=getIcon("arrow_down"))
		row.operator("object.move_uv_down_operator", text="", icon_value=getIcon("arrow_up"))
		
		

def register():
	bpy.utils.register_class(ApplyTextureFaceOperator)
	bpy.utils.register_class(ApplyTextureFaceAlphaOperator)
	bpy.utils.register_class(RotateUVOperator)
	bpy.utils.register_class(ShrinkUVOperator)
	bpy.utils.register_class(ShrinkUVHorizontalOperator)
	bpy.utils.register_class(ShrinkUVVerticalOperator)
	bpy.utils.register_class(ExpandUVOperator)
	bpy.utils.register_class(ExpandUVHorizontalOperator)
	bpy.utils.register_class(ExpandUVVerticalOperator)
	bpy.utils.register_class(MoveUVUpOperator)
	bpy.utils.register_class(MoveUVDownOperator)
	bpy.utils.register_class(MoveUVLeftOperator)
	bpy.utils.register_class(MoveUVRightOperator)
	bpy.utils.register_class(NightzMapperToolsPanel)


def unregister():
	bpy.utils.unregister_class(ApplyTextureFaceOperator)
	bpy.utils.unregister_class(ApplyTextureFaceAlphaOperator)
	bpy.utils.unregister_class(RotateUVOperator)
	bpy.utils.unregister_class(ShrinkUVOperator)
	bpy.utils.unregister_class(ShrinkUVHorizontalOperator)
	bpy.utils.unregister_class(ShrinkUVVerticalOperator)
	bpy.utils.unregister_class(ExpandUVOperator)
	bpy.utils.unregister_class(ExpandUVHorizontalOperator)
	bpy.utils.unregister_class(ExpandUVVerticalOperator)
	bpy.utils.unregister_class(MoveUVUpOperator)
	bpy.utils.unregister_class(MoveUVDownOperator)
	bpy.utils.unregister_class(MoveUVLeftOperator)
	bpy.utils.unregister_class(MoveUVRightOperator)
	bpy.utils.unregister_class(NightzMapperToolsPanel)


if __name__ == "__main__":
    register()
