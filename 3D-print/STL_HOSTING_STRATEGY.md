# STL Hosting & Distribution Strategy

## Problem
- STL files are too large for GitHub Pages
- Must be gated behind paid access (STL tier $29, Course $97, Bundle $349)
- Need reliable, fast, easy-to-manage delivery

## Recommended: Google Drive + Portal Integration

### Setup
1. **Create Google Drive folder**: `3D Print Academy - Student Downloads`
2. **Subfolder structure**:
   ```
   📁 3D Print Academy - Student Downloads/
   ├── 📁 Baby Milestone Frames (1-12 months)/
   │   ├── month-01.stl
   │   ├── month-02.stl
   │   └── ... (12 files)
   ├── 📁 General Frames/
   │   ├── 4x6-magnet-frame.stl
   │   ├── instax-mini-magnet-frame.stl
   │   ├── hexagon-magnet-frame.stl
   │   ├── heart-magnet-frame.stl
   │   ├── circle-magnet-frame.stl
   │   ├── star-magnet-frame.stl
   │   └── collage-3-photo-frame.stl
   └── 📁 OpenSCAD Sources/
       ├── baby-milestone-frame.scad
       ├── 4x6-magnet-frame.scad
       └── ... (all .scad files)
   ```

3. **Sharing**: Set folder to "Anyone with the link can view"
4. **Portal integration**: Add download links in portal behind tier check

### Implementation in Portal
```javascript
// In portal/index.html - add to downloads section
const STL_DOWNLOADS = {
  driveFolder: 'GOOGLE_DRIVE_FOLDER_ID',
  files: {
    'baby-milestones': {
      name: 'Baby Milestone Frames (1-12 months)',
      driveId: 'DRIVE_FILE_ID',
      tier: ['stl', 'course', 'bundle', 'admin']
    },
    'general-frames': {
      name: 'General Magnet Photo Frames (7 designs)',
      driveId: 'DRIVE_FILE_ID',
      tier: ['stl', 'course', 'bundle', 'admin']
    },
    'scad-sources': {
      name: 'OpenSCAD Source Files (customizable)',
      driveId: 'DRIVE_FILE_ID',
      tier: ['course', 'bundle', 'admin']
    }
  }
};
```

## File Inventory

### Baby Milestone Frames (12 files, ~3MB total)
| File | Size | Description |
|------|------|-------------|
| month-01.stl | 164K | "1 MONTH" frame |
| month-02.stl | 260K | "2 MONTHS" frame |
| month-03.stl | 276K | "3 MONTHS" frame |
| month-04.stl | 230K | "4 MONTHS" frame |
| month-05.stl | 253K | "5 MONTHS" frame |
| month-06.stl | 272K | "6 MONTHS" frame |
| month-07.stl | 234K | "7 MONTHS" frame |
| month-08.stl | 289K | "8 MONTHS" frame |
| month-09.stl | 273K | "9 MONTHS" frame |
| month-10.stl | 272K | "10 MONTHS" frame |
| month-11.stl | 228K | "11 MONTHS" frame |
| month-12.stl | 267K | "12 MONTHS" frame |

### General Frames (7 files, ~878K total)
| File | Size | Description |
|------|------|-------------|
| 4x6-magnet-frame.stl | 100K | Standard 4x6 inch photo |
| instax-mini-magnet-frame.stl | 103K | Fuji Instax Mini print |
| hexagon-magnet-frame.stl | 64K | Trendy hex shape |
| heart-magnet-frame.stl | 109K | Heart shape |
| circle-magnet-frame.stl | 245K | Round frame |
| star-magnet-frame.stl | 138K | Star shape |
| collage-3-photo-frame.stl | 119K | 3-photo collage |

### Magnet Specifications (all frames)
- Magnet type: 6mm x 2mm neodymium disc magnets
- Slot diameter: 6.2mm (0.2mm tolerance for press-fit)
- Slot depth: 2.2mm (0.2mm for glue)
- Recommended: N52 grade for maximum hold

### Print Settings (recommended)
- Material: PLA+ (eSun, Polymaker, or Overture)
- Layer height: 0.2mm
- Infill: 15-20% (frames are mostly solid borders)
- Supports: None needed (designed for supportless printing)
- Print time: 30-90 min per frame depending on size
- Orientation: Print flat (face down)

## Audio/Video Content

### NotebookLM Generated Content
- **Audio Overview**: `content/audio/course-overview-audio.m4a` (46MB)
  - Title: "Make $15,000 monthly printing magnetic frames"
  - Generated from 3 sources covering filaments, tolerances, and business strategy
- **Video Overview**: Still generating in NotebookLM (cinematic format)
  - Notebook: https://notebooklm.google.com/notebook/2738221b-0376-4652-835e-a09e7be5b469

## Future Expansion
- Add seasonal frame sets (Christmas, Halloween, Easter)
- Custom text frame generator (wedding dates, baby names)
- Photo frame with built-in stand/easel option
- Multi-size frame kits (3x5, 4x6, 5x7, 8x10)
