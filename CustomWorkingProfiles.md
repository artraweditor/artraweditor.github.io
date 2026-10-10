# Using custom working profiles

By default ART offers six working profiles in the *Color → Color Management → Working profile* combo box:
`sRGB`, `Adobe RGB`, `ProPhoto`, `Rec2020`, `ACESp0` and `ACESp1`.
If you need a different RGB space (for example a camera-specific gamut, or the working space of another application), you can add your own by creating a small JSON file called `workingspaces.json`.

<a name="where"></a>
## Where to put the file

ART looks for a file named exactly `workingspaces.json` in two folders, in this order:

1. the `iccprofiles` folder inside the ART installation (the one shipped with the program);
2. the **ICC profiles directory** set by the user, i.e. the folder chosen in *Preferences → Color Management → ICC profiles directory*.

For a personal setup, just put `workingspaces.json` in the ICC profiles directory you have configured in the preferences.
If both files exist, both are read; a name defined by the first one cannot be redefined by the second (see [below](#notes)).

The file is read once, at program startup: **restart ART** after creating or editing it.

<a name="format"></a>
## File format

The file is a JSON document with a single top-level key, `working_spaces`, containing a list of objects. Each object describes one working space and has a `name` plus *either* a `matrix` *or* a `file`:

```json
{
    "working_spaces": [
        {
            "name": "My Space (from ICC)",
            "file": "My_Space.icc"
        },
        {
            "name": "My Space (from matrix)",
            "matrix": [
                0.6734241, 0.1656411, 0.1251286,
                0.2790177, 0.6753402, 0.0456377,
               -0.0019300, 0.0299784, 0.7973330
            ]
        }
    ]
}
```

| key | type | meaning |
|---|---|---|
| `name` | string | the label shown in the *Working profile* combo box, and the string stored in the processing profile (`.arp`). Required. |
| `matrix` | array of 9 numbers | the RGB → XYZ matrix of the space (see [below](#matrix)). |
| `file` | string | path to an ICC profile from which the matrix is extracted (see [below](#icc)). Only used if `matrix` is absent. |

C-style comments (`// ...` and `/* ... */`) are accepted in the file, since it is minified before parsing.

<a name="icc"></a>
## Defining a space from an ICC profile

Use `file` to point to an ICC profile. The path can be:

- **absolute**, or
- **relative**, in which case it is resolved relative to the folder that contains `workingspaces.json`.

ART only uses the *primaries* of the profile: the three colorant tags (`rXYZ`, `gXYZ`, `bXYZ`) are read and turned into the matrix. The profile must therefore satisfy two requirements:

- it must be an **RGB** profile;
- it must be a **matrix/TRC (matrix-shaper)** profile. LUT-based profiles (as used for some cameras, printers or scanners) are rejected.

The tone curves of the profile are **ignored**: the resulting working space is always **linear** (gamma 1.0), like the built-in ones. So, for instance, pointing to the ICC file of a gamma-2.2 space gives you that space's gamut with a linear encoding.

<a name="matrix"></a>
## Defining a space from a matrix

Use `matrix` to give the primaries directly. It must be a **flat list of exactly 9 numbers**, listing a 3×3 matrix **row by row**:

```
[ Xr, Xg, Xb,
  Yr, Yg, Yb,
  Zr, Zg, Zb ]
```

i.e. the matrix that converts linear RGB in your space into XYZ, where the columns are the XYZ coordinates of the red, green and blue primaries. Note that:

- the XYZ values must be relative to the **D50** illuminant (the ICC profile connection space), so that the white of the space, `(1,1,1)`, maps to D50 `(0.9642, 1.0, 0.8249)`. Primaries defined against D65 must be chromatically adapted (e.g. with Bradford) first. This is the same convention used by the ICC colorant tags, so the numbers can be copied directly from the `rXYZ`/`gXYZ`/`bXYZ` tags of a profile, or from tables such as the "D50" matrices on [Bruce Lindbloom's site](http://www.brucelindbloom.com/index.html?Eqn_RGB_XYZ_Matrix.html);
- negative entries are allowed (the Rec2020 matrix above has one);
- the matrix must be invertible;
- nested arrays (`[[...],[...],[...]]`) are **not** accepted: write the nine numbers in a single list. Fewer or more than nine numbers is an error.

<a name="notes"></a>
## Things to know

- **Name clashes are ignored.** If a name is already defined (either one of the six built-in spaces, or one coming from an earlier file or entry), the new entry is silently skipped. Choose a unique name.
- **Name is what is saved.** The name is stored in processing profiles, so if you rename or remove a space, images using it will fall back to the default working space (Rec2020).
- **Entries that cannot be used are skipped**, with the others still being loaded. This happens when the ICC file is missing, is not an RGB matrix-shaper profile, or the matrix is singular.
- **Syntax errors stop the loading of the file.** If the JSON is malformed, if `working_spaces` is missing, if an entry has no `name`, if `matrix` is not a list of nine numbers, or if an entry has neither `matrix` nor a string `file`, ART stops reading the rest of the file. Entries that precede the faulty one have already been added.
- The new spaces appear in the combo box in alphabetical (case-sensitive) order, mixed with the built-in ones.

<a name="troubleshooting"></a>
## Troubleshooting

Run ART from a terminal with verbose output enabled: pass `-V` to `ART-cli`, or, for the GUI, set `Verbose=true` in the `[General]` section of the `options` file. While loading, ART prints lines like

```
trying to load extra working spaces from /path/to/iccprofiles/workingspaces.json OK
Added working space: My Space (from matrix)
  matrix: [ [ 0.673424 0.165641 0.125129 ] [ 0.279018 0.67534 0.0456377 ] [ -0.00193 0.0299784 0.797333 ] ]
```

The possible outcomes are:

| message | meaning |
|---|---|
| `... FAIL` | the file does not exist, is empty, or is not valid JSON: check the location and the syntax |
| `... ERROR in parsing ...` | the structure is wrong (see the list of syntax errors above) |
| `Could not find suitable matrix for working space: <name>` | the ICC file in `file` is missing, is not RGB, or is not a matrix-shaper profile |
| `Matrix for working space: <name> is not invertible, skipping` | the three primaries are degenerate (e.g. collinear, or a zero row) |
| `Added working space: <name>` | success; the printed matrix is the one that was used |
