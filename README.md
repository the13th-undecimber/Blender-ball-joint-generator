# Ball Joint Maker

A Blender extension that generates ball joints (a ball plus a stem) and cuts matching sockets into other meshes. Sockets are previewed with Boolean modifiers first and applied only when you finalize them.

Designed for printable figures, models and mechanical parts that need a ball joint with a defined clearance.

## Features

- Generates a ball joint at the selected object or the 3D cursor. Ball: sphere, cylinder or cube. Stem: cylinder, ellipsoid, flat cylinder or square prism.
- Previews the socket on any number of target meshes, non-destructively.
- Clearance is added to the cutter size, so the socket is always slightly larger than the ball.
- Optional cutout per joint, for example a slot that lets the stem swing.
- Each joint keeps its own shape values. Editing one joint never changes another.
- Update Preview rebuilds only the mesh data. Position, rotation and target previews are kept.
- Finalize keeps a hidden backup copy of each target.

## Requirements

- Blender 4.2 or later
- Automated tests pass on Blender 4.2.23 LTS, 5.0.1 and 5.1.0

## Installation

1. Download `ball_joint_maker-<version>.zip` from the Releases page. Do not unzip it.
2. In Blender, go to **Edit › Preferences › Get Extensions**.
3. Open the **⌄** menu at the top right and choose **Install from Disk…**.
4. Select the zip file.

The panel appears in the 3D Viewport sidebar (press **N**) under the **Joint Maker** tab.

## Quick start

1. **1) Joints:** Click **Generate Joint**. A ball and stem are created at the selected object (or the 3D cursor), and the new joint becomes the edited joint.
2. **2) Shape:** Adjust the values, then click **Update Preview** in the panel header. The button turns red while changes are not applied.
3. Move and rotate the ball to place the joint. Rotate the stem to change its direction; it pivots around the ball center.
4. **3) Target:** Select the mesh that should receive the socket, then click **Preview Socket on Target**.
5. **4) Apply:** Click **Finalize** to cut the socket into the target and remove the cutters. Optionally, click **Apply Stem** to merge the stem into the ball.

## Panel reference

### 1) Joints

| Control | What it does |
| --- | --- |
| J001 – J006 | Choose the joint to edit. Buttons for joints that do not exist are greyed out. Selecting any part of a joint in the viewport also makes it the edited joint. |
| Editing box | Shows the joint's status (*editing*, *stem applied*, *finalized*) and the targets that preview its socket. |
| Select: Ball / Stem / Cutout | Select that part of the edited joint. Useful because the stem sits inside the ball. |
| Generate Joint | Creates a new joint from the values currently shown. |

### 2) Shape

The header shows **Update Preview → J00x**. It rebuilds the edited joint from its values and turns red when the values changed since the last update.

The panel shows which values you are editing:

- **J00x values** – the values of the edited joint.
- **Values for the next new joint** – shown when no joint is being edited.

| Sub-panel | Values |
| --- | --- |
| (top) | Segments, plus a reset button that restores the defaults |
| Ball | Shape (Sphere / Cylinder / Cube) and radius. Cylinder and Cube can scale the top or bottom face in XY. |
| Stem | Shape (Cylinder / Sphere / Flat Cylinder / Cube), radius and length. Flat Cylinder also has Flatness. Cylinder, Cube and Flat Cylinder can scale the top or bottom face. |
| Clearance | Added to the cutter size on each axis. This is added to the **diameter**, so the gap on each side is half the value. |
| Cutout | The checkbox in the header turns the cutout on or off for the edited joint. Shape (Box, or Cylinder along Y) and size X / Y / Z. |

When you turn a cutout on, it is created at the ball center and selected, so you can move and rotate it right away. If you turn it off and on again, it returns to its last position.

### 3) Target

| Control | What it does |
| --- | --- |
| Preview Socket on Target | Adds the edited joint's socket (and cutout) to the selected meshes as Boolean modifiers. |
| Preview Sockets of All Joints | Does the same for every joint. |
| Show Socket Preview | Hides or shows all socket previews and cutter objects. Turn it off if the viewport becomes slow. |

### 4) Apply

| Control | What it does | Afterwards |
| --- | --- | --- |
| Apply Stem | Merges the stem into the ball and deletes the stem. Asks for confirmation. | The joint's shape can no longer be updated. |
| Finalize | Applies the previewed sockets to all targets of the edited joint and deletes its cutters and cutout. Asks for confirmation. | The socket can no longer be moved or resized. |
| Finalize All Joints | Finalizes every joint that has a target. | Same as above |

Before a target is finalized for the first time, a hidden copy without modifiers is kept as `<name>_preFinalize`. Other modifiers on the target are left untouched.

## How values work

- Each joint stores its own shape values on its collection (`BJG_Joint001` and so on).
- A new joint copies the values shown on screen when it is created. After that it is independent.
- Changing values does not change the mesh until you click **Update Preview**.
- Position and rotation are not part of the values; they belong to the objects.

## Objects created

| Object | Role |
| --- | --- |
| `BJG_Ball###` | The ball (the part you keep) |
| `BJG_Stem###` | The stem, a child of the ball, merged by a Union modifier |
| `BJG_BallCutter###`, `BJG_StemCutter###` | Cutters: ball and stem enlarged by the clearance |
| `BJG_Cutout###` | Optional cutout, a child of the ball |

All parts are stored in the `BJG_Joints › BJG_Joint###` collections. Helper parts are drawn as wireframes and excluded from renders.

The modifiers on targets are named `BJG_Socket_J###` and `BJG_Cutout_J###`.

Parts are tracked by tags, not names, so renaming them is safe. To delete a joint completely, delete all of its parts. Its number is reused by the next joint you generate.

## Preferences

In **Edit › Preferences › Add-ons › Ball Joint Maker**:

- **Show hint after generating** – shows a short hint about Update Preview after each Generate Joint. The hint dialog also has a "Don't show this again" checkbox.

## Notes and limitations

- Up to 6 joints per scene.
- Works in Object Mode only.
- Sockets use the Exact Boolean solver. It is accurate but can be slow on dense meshes.
- Targets with shape keys cannot be finalized.

## Building from source

The extension is the `ball_joint_maker` folder. Either zip its contents (with `blender_manifest.toml` at the top of the zip), or use Blender's build command:

```
blender --command extension build --source-dir ball_joint_maker
```

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).

## Changelog

### 2.2.0
- The interface is now in English.

### 2.1.1
- Update Preview moved to the Shape panel header; it turns red when changes are not applied.
- Shape values are grouped into Ball, Stem, Clearance and Cutout sub-panels.
- A hint is shown after generating a joint; it can be turned off.

### 2.1.0
- Each joint now has its own values. Removed shared/local values and joint scope checkboxes.
- Added an "edited joint" that follows the selection.
- Buttons show the joint they act on.

### 2.0.0
- Complete rewrite. Update Preview replaces mesh data only, so transforms are preserved.
