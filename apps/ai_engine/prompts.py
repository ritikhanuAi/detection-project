"""Prompt templates and class definitions for RoadAthena AI."""

STAGE1_ROAD_PROFILING_PROMPT = """
You are an expert road and transportation civil engineer analyzing a video frame from a road inspection survey.
Analyze the road in this image and extract exactly these 5 road profile attributes:

1. "road_type": Must be one of ["Highway", "Urban", "Rural"] or null if unclear.
   - Highway: Multi-lane divided expressway, controlled access, high-speed road, or grade-separated.
   - Urban: City/town streets, pedestrian paths, curbs, streetlights, buildings/commercial roadside.
   - Rural: Countryside, farmland/forest roadside, minimal roadside infrastructure, uncurbed.
2. "pavement_type": Must be one of ["Asphalt", "Concrete"] or null if unclear.
   - Asphalt: Dark gray or black bituminous surface, flexible pavement.
   - Concrete: Light gray or off-white rigid pavement panels with transverse joint seams.
3. "carriageway_type": Must be one of ["Divided", "Undivided"] or null if unclear.
   - Divided: Opposing traffic separated by a physical median, barrier, grass strip, or wide island.
   - Undivided: Opposing traffic separated only by paint markings or no median barrier.
4. "lanes": Integer count of total visible lanes in this direction/roadway (e.g. 1, 2, 3, 4). If unclear, estimate best integer.
5. "estimated_width_m": Estimated total roadway width in meters (float, e.g. 7.5, 12.0). Standard lane is ~3.0m - 3.75m.

Return STRICTLY a JSON object matching this schema with no markdown formatting:
{
  "road_type": "Highway" | "Urban" | "Rural" | null,
  "pavement_type": "Asphalt" | "Concrete" | null,
  "carriageway_type": "Divided" | "Undivided" | null,
  "lanes": integer,
  "estimated_width_m": float,
  "explanation": "Brief 1-sentence visual justification"
}
"""

STAGE2_VALIDATION_PROMPT_TEMPLATE = """
You are an expert road pavement defect and damage inspector.
You are evaluating a proposed object detection labeled by a computer vision model.

Proposed Defect Class: "{class_name}"
Contextual Guidelines:
- "pothole" / "D20": A distinct bowl-shaped cavity or depression in the pavement surface with sharp vertical edges and dark depth/shadow.
- "crack" / "longitudinal crack" / "transverse crack" / "D00": Distinct linear fracture line propagating across or along pavement.
- "alligator cracking" / "fatigue crack" / "D10": Interconnected network or web of cracks resembling reptile skin or chicken wire.
- "rutting" / "D40": Surface depression along vehicle wheelpaths.
- "manhole" / "utility cover": Circular or rectangular metal utility casting.

CRITICAL - WATCH OUT FOR LOOK-ALIKES & FALSE POSITIVES:
- Shadows from trees, overpasses, light poles, or vehicles.
- Tar sealant lines / crack repair patches / smooth mastic.
- Wet surface patches, oil stains, or puddle reflections.
- Lane line markings, thermoplastic paint chips, road seams/expansion joints.
- Normal aggregate texture variation or debris/leaves on the road.

Review the attached crop image (and context).
Decide whether the proposed class "{class_name}" is genuinely present:
1. "Correct": The visual evidence clearly and unambiguously shows a real {class_name}.
2. "Incorrect/False": The detection is false. The region is actually a look-alike (shadow, oil, repair patch, clean pavement, marking, etc.) or completely different object.
3. "Needs Review": The image is too blurry, low-resolution, occluded, or visually ambiguous to make a definitive determination.

Return STRICTLY a JSON object matching this schema with no markdown formatting:
{{
  "status": "Correct" | "Incorrect/False" | "Needs Review",
  "confidence": float between 0.0 and 1.0,
  "reason": "Clear, concise technical reason explaining visible pavement texture, defect presence, or confounding visual factor"
}}
"""
