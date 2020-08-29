import bpy, json

def delete_all():
    for item in bpy.data.objects:
        bpy.data.objects[item.name].select_set(True)
        bpy.ops.object.delete(use_global=True)

def Material(message):
    print(message)
    assert message['class']=='Material'
