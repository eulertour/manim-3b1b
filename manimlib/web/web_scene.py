from manimlib.scene.scene import PyScene


class Scene(PyScene):
    def render(self):
        # Regular Scenes render upon instantiation.
        return super(Scene, self).__init__()

    def dump_frames(self):
        return self.camera.frame_data
