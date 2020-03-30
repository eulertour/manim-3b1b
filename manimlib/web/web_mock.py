import os.path

def tex2points(tex):
    if tex == '.':
        tex = 'LINUX_CURRENT_DIR'
    try:
        with open(os.path.join('manimlib', 'web', 'tex_points', tex)) as f:
            return eval(f.read())
    except FileNotFoundError:
        print(f"No points cached for {tex}")
        return []
