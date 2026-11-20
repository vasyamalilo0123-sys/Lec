# Переліки сіток BodyParts3D для сцен мозку. Суфікси: R — права півкуля, L — ліва.
CORTEX = {
    'R': ['FMA72653', 'FMA72655', 'FMA72661', 'FMA72665', 'FMA72667', 'FMA72669', 'BP50', 'FMA72975', 'FMA72685', 'FMA72687',
          'FMA72800', 'FMA72804', 'FMA72689', 'FMA72705', 'FMA72717', 'FMA72977', 'FMA72701'],
    'L': ['FMA72654', 'FMA72656', 'FMA72662', 'FMA72666', 'FMA72668', 'FMA72670', 'BP49', 'FMA72976', 'FMA72686', 'FMA72688',
          'FMA72801', 'FMA72805', 'FMA72690', 'FMA72706', 'FMA72718', 'FMA72978', 'FMA72702'],
}
BOTH = ['BP51']                    # очноямкові звивини + пряма звивина, одна сітка на обидві півкулі
WHITE = 'FMA61822'                 # біла речовина півкуль
CEREBELLUM, PONS, MEDULLA, MIDBRAIN, PEDUNCLE = 'FMA67944', 'FMA67943', 'FMA62004', 'FMA61993nsn', 'FMA62394'
CALLOSUM = 'FMA86464'
DEEP = {'thalamusR': 'FMA258714', 'thalamusL': 'FMA258716', 'hypothalamus': 'FMA62008nsn', 'pituitary': 'FMA13889', 'pineal': 'FMA62033',
        'fornixR': 'FMA72924', 'fornixL': 'FMA72925', 'septum': 'FMA61844', 'mammillary': 'FMA74877',
        'ventLR': 'FMA78449', 'ventLL': 'FMA78450', 'vent3': 'FMA78454', 'vent4': 'FMA78469', 'aqueduct': 'FMA78467',
        'choroidR': 'FMA274027', 'choroidL': 'FMA274029', 'chiasm': 'FMA62045'}


def tissues(C, bp3d):
    """Матеріали живого мозку."""
    return {
        'cortex': bp3d.flesh(C, 'cortex', (0.60, 0.36, 0.33), (0.74, 0.52, 0.46), rough=0.36, sss=0.85, scale=0.02, bump=0.35, noise=22, coat=0.5),
        'white': bp3d.flesh(C, 'white', (0.80, 0.70, 0.62), (0.88, 0.80, 0.72), rough=0.45, sss=0.7, scale=0.02, bump=0.15, noise=30, coat=0.3),
        'cerebellum': bp3d.flesh(C, 'cerebellum', (0.56, 0.30, 0.28), (0.68, 0.42, 0.38), rough=0.36, sss=0.85, scale=0.02, bump=0.3, noise=40, coat=0.5),
        'stem': bp3d.flesh(C, 'stem', (0.74, 0.58, 0.50), (0.84, 0.70, 0.60), rough=0.4, sss=0.7, scale=0.02, bump=0.2, noise=35, coat=0.4),
    }


def columns(left, right, xl=520, xr=1510, y0=380, y1=940):
    """Розкладає підписи у дві колонки без перетину виносок: у кожній колонці порядок згори донизу — за висотою точки в кадрі.
    left/right: списки (текст, точка xyz). Повертає labels для compose.js."""
    import bpy
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    sc = bpy.context.scene
    out = []
    for items, x, align in ((left, xl, 'right'), (right, xr, 'left')):
        items = sorted(items, key=lambda it: -world_to_camera_view(sc, sc.camera, Vector(it[1])).y)
        n = len(items)
        for i, (text, p) in enumerate(items):
            y = y0 if n == 1 else y0 + (y1 - y0) * i / (n - 1)
            out.append({'text': text, 'p': tuple(p), 'at': [x, round(y)], 'align': align})
    return out
