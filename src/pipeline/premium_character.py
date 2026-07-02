# ============================================================
# src/pipeline/premium_character.py
# Premium looking cartoon characters using PIL
# ============================================================

import sys
import os
if __name__ == "__main__":
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(os.path.dirname(_current_dir))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

import math
from typing import Tuple


def draw_premium_character(
    draw,
    center_x: int,
    ground_y: int,
    scale: float,
    character_type: str,
    color: Tuple[int, int, int],
    emotion: str = "neutral",
    speaking_frame: int = 0,
):
    """
    Draw a premium-looking cartoon character
    
    character_type: HERO, HEROINE, VILLAIN, CHILD, OLD_MAN, NARRATOR
    """
    
    # Scale-based measurements
    head_size = int(80 * scale)
    body_height = int(180 * scale)
    body_width = int(100 * scale)
    arm_length = int(120 * scale)
    leg_length = int(140 * scale)
    
    # Colors
    skin_tones = {
        "HERO": (255, 220, 177),
        "HEROINE": (255, 224, 189),
        "VILLAIN": (200, 180, 160),
        "CHILD": (255, 228, 196),
        "OLD_MAN": (240, 210, 180),
        "NARRATOR": (245, 215, 185),
    }
    
    skin = skin_tones.get(character_type, (255, 220, 177))
    
    hair_colors = {
        "HERO": (60, 40, 20),
        "HEROINE": (100, 60, 30),
        "VILLAIN": (30, 30, 30),
        "CHILD": (139, 69, 19),
        "OLD_MAN": (200, 200, 200),
        "NARRATOR": (80, 60, 40),
    }
    hair = hair_colors.get(character_type, (60, 40, 20))
    
    clothing_color = color
    clothing_dark = tuple(max(0, c - 60) for c in color)
    clothing_light = tuple(min(255, c + 30) for c in color)
    
    # ===== POSITIONS =====
    head_y = ground_y - leg_length - body_height - head_size
    body_top_y = head_y + head_size
    body_bottom_y = body_top_y + body_height
    leg_top_y = body_bottom_y
    
    # ===== LEGS FIRST (behind body) =====
    pant_color = (40, 40, 80)
    pant_light = (60, 60, 120)
    
    # Left leg
    leg_x_offset = int(20 * scale)
    draw_leg(draw, center_x - leg_x_offset, leg_top_y, leg_length, 
             int(25 * scale), pant_color, pant_light)
    # Right leg
    draw_leg(draw, center_x + leg_x_offset, leg_top_y, leg_length,
             int(25 * scale), pant_color, pant_light)
    
    # Shoes
    shoe_color = (20, 20, 20)
    shoe_light = (60, 60, 60)
    draw_shoe(draw, center_x - leg_x_offset, leg_top_y + leg_length, 
              int(35 * scale), shoe_color, shoe_light)
    draw_shoe(draw, center_x + leg_x_offset, leg_top_y + leg_length,
              int(35 * scale), shoe_color, shoe_light)
    
    # ===== BODY (Torso) =====
    draw_torso(draw, center_x, body_top_y, body_bottom_y, body_width,
               clothing_color, clothing_dark, clothing_light)
    
    # ===== ARMS =====
    shoulder_y = body_top_y + int(15 * scale)
    left_shoulder_x = center_x - body_width // 2
    right_shoulder_x = center_x + body_width // 2
    
    # Arm positions based on emotion
    left_arm_end, right_arm_end = get_arm_positions(
        left_shoulder_x, right_shoulder_x, shoulder_y, arm_length, emotion, scale
    )
    
    # Draw arms
    draw_arm(draw, left_shoulder_x, shoulder_y, left_arm_end, 
             int(20 * scale), clothing_color, clothing_dark, skin)
    draw_arm(draw, right_shoulder_x, shoulder_y, right_arm_end,
             int(20 * scale), clothing_color, clothing_dark, skin)
    
    # ===== HEAD =====
    draw_premium_head(draw, center_x, head_y, head_size, skin, hair, 
                      emotion, speaking_frame, character_type)


def draw_leg(draw, x, y, length, width, color, light_color):
    """Draw a leg with cylinder look"""
    # Main leg
    draw.rectangle(
        [x - width, y, x + width, y + length],
        fill=color
    )
    # Highlight on left side
    draw.rectangle(
        [x - width, y, x - width + 5, y + length],
        fill=light_color
    )
    # Shadow on right side
    draw.rectangle(
        [x + width - 5, y, x + width, y + length],
        fill=tuple(max(0, c - 20) for c in color)
    )


def draw_shoe(draw, x, y, size, color, light):
    """Draw a shoe"""
    # Shoe base (oval)
    draw.ellipse(
        [x - size, y - 5, x + size, y + 20],
        fill=color,
        outline=(0, 0, 0),
        width=2
    )
    # Shoe highlight
    draw.ellipse(
        [x - size + 5, y - 3, x - size + 15, y + 5],
        fill=light
    )


def draw_torso(draw, x, top_y, bottom_y, width, main_color, dark, light):
    """Draw a stylized torso"""
    half_width = width // 2
    
    # Main body (with rounded top)
    # Shoulders (rounded rectangle top)
    draw.rectangle(
        [x - half_width, top_y + 20, x + half_width, bottom_y],
        fill=main_color
    )
    
    # Shoulder curves
    draw.ellipse(
        [x - half_width - 5, top_y, x - half_width + 30, top_y + 40],
        fill=main_color
    )
    draw.ellipse(
        [x + half_width - 30, top_y, x + half_width + 5, top_y + 40],
        fill=main_color
    )
    
    # Highlight (left side - gives 3D look)
    draw.rectangle(
        [x - half_width, top_y + 20, x - half_width + 15, bottom_y],
        fill=light
    )
    
    # Shadow (right side)
    draw.rectangle(
        [x + half_width - 15, top_y + 20, x + half_width, bottom_y],
        fill=dark
    )
    
    # Neck opening (V-neck style)
    neck_points = [
        (x - 15, top_y + 15),
        (x, top_y + 40),
        (x + 15, top_y + 15),
    ]
    # Skin colored V
    draw.polygon(neck_points, fill=(255, 220, 177))
    
    # Outline
    draw.rectangle(
        [x - half_width, top_y + 20, x + half_width, bottom_y],
        outline=(0, 0, 0),
        width=3
    )


def get_arm_positions(left_x, right_x, shoulder_y, arm_length, emotion, scale):
    """Get arm end positions based on emotion"""
    
    if emotion in ["happy", "excited"]:
        # Arms UP in celebration
        left_end = (left_x - int(30 * scale), shoulder_y - arm_length)
        right_end = (right_x + int(30 * scale), shoulder_y - arm_length)
    elif emotion in ["angry", "furious"]:
        # Arms on hips (bent)
        left_end = (left_x - int(50 * scale), shoulder_y + int(60 * scale))
        right_end = (right_x + int(50 * scale), shoulder_y + int(60 * scale))
    elif emotion in ["surprised", "shocked"]:
        # Arms spread wide
        left_end = (left_x - arm_length, shoulder_y - int(30 * scale))
        right_end = (right_x + arm_length, shoulder_y - int(30 * scale))
    elif emotion in ["sad", "crying"]:
        # Arms down, close to body
        left_end = (left_x - int(10 * scale), shoulder_y + arm_length)
        right_end = (right_x + int(10 * scale), shoulder_y + arm_length)
    elif emotion == "confident":
        # Arms crossed
        left_end = (right_x - int(20 * scale), shoulder_y + int(40 * scale))
        right_end = (left_x + int(20 * scale), shoulder_y + int(40 * scale))
    else:
        # Neutral - arms slightly out
        left_end = (left_x - int(20 * scale), shoulder_y + arm_length - int(20 * scale))
        right_end = (right_x + int(20 * scale), shoulder_y + arm_length - int(20 * scale))
    
    return left_end, right_end


def draw_arm(draw, shoulder_x, shoulder_y, end_pos, width, main_color, dark, skin):
    """Draw an arm with hand"""
    end_x, end_y = end_pos
    
    # Calculate midpoint (elbow)
    mid_x = (shoulder_x + end_x) // 2
    mid_y = (shoulder_y + end_y) // 2
    
    # Upper arm (sleeve)
    draw_thick_line(draw, shoulder_x, shoulder_y, mid_x, mid_y, width, main_color, dark)
    
    # Lower arm (skin)
    draw_thick_line(draw, mid_x, mid_y, end_x, end_y, width - 5, skin, 
                    tuple(max(0, c - 30) for c in skin))
    
    # Hand (circle)
    hand_size = int(width * 0.7)
    draw.ellipse(
        [end_x - hand_size, end_y - hand_size,
         end_x + hand_size, end_y + hand_size],
        fill=skin,
        outline=(80, 60, 40),
        width=2
    )


def draw_thick_line(draw, x1, y1, x2, y2, width, color, dark_color):
    """Draw a thick line with 3D effect"""
    # Main line
    draw.line([x1, y1, x2, y2], fill=color, width=width)
    
    # Highlight (thinner line, slightly offset)
    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx*dx + dy*dy)
    if length > 0:
        # Perpendicular offset
        offset_x = -dy / length * 3
        offset_y = dx / length * 3
        
        draw.line(
            [x1 + offset_x, y1 + offset_y, x2 + offset_x, y2 + offset_y],
            fill=tuple(min(255, c + 30) for c in color),
            width=2
        )


def draw_premium_head(draw, center_x, top_y, size, skin, hair, emotion, 
                       speaking_frame, character_type):
    """Draw a premium cartoon head"""
    
    center_y = top_y + size // 2
    
    # ===== FACE (oval shape, wider than tall) =====
    face_width = int(size * 1.1)
    face_height = size
    
    draw.ellipse(
        [center_x - face_width, center_y - face_height,
         center_x + face_width, center_y + face_height],
        fill=skin,
        outline=(80, 60, 40),
        width=3
    )
    
    # Face highlight (subtle, on left)
    draw.ellipse(
        [center_x - face_width + 10, center_y - face_height + 15,
         center_x - face_width + 40, center_y + 10],
        fill=tuple(min(255, c + 15) for c in skin)
    )
    
    # ===== HAIR (based on character) =====
    if character_type == "HEROINE":
        # Long hair
        draw.ellipse(
            [center_x - face_width - 10, center_y - face_height - 20,
             center_x + face_width + 10, center_y + face_height + 40],
            fill=hair,
            outline=(0, 0, 0),
            width=2
        )
        # Front face still shows
        draw.ellipse(
            [center_x - face_width + 5, center_y - face_height + 15,
             center_x + face_width - 5, center_y + face_height - 5],
            fill=skin
        )
        # Hair on top
        draw.arc(
            [center_x - face_width - 5, center_y - face_height - 15,
             center_x + face_width + 5, center_y + 10],
            180, 360, fill=hair, width=15
        )
    elif character_type == "OLD_MAN":
        # Bald with side hair
        draw.arc(
            [center_x - face_width - 5, center_y - face_height + 20,
             center_x + face_width + 5, center_y + 30],
            180, 360, fill=hair, width=10
        )
        # Mustache/beard
        draw.arc(
            [center_x - 30, center_y + 20,
             center_x + 30, center_y + 60],
            0, 180, fill=hair, width=6
        )
    elif character_type == "CHILD":
        # Short messy hair
        for i in range(-3, 4):
            x = center_x + i * 12
            draw.ellipse(
                [x - 15, center_y - face_height - 10,
                 x + 15, center_y - face_height + 25],
                fill=hair
            )
    elif character_type == "VILLAIN":
        # Slicked back hair
        draw.polygon(
            [(center_x - face_width, center_y - face_height + 20),
             (center_x + face_width, center_y - face_height + 20),
             (center_x + face_width + 10, center_y - face_height - 5),
             (center_x - face_width - 10, center_y - face_height - 5)],
            fill=hair,
            outline=(0, 0, 0)
        )
    else:
        # Normal short hair
        draw.arc(
            [center_x - face_width - 5, center_y - face_height - 15,
             center_x + face_width + 5, center_y + 30],
            180, 360, fill=hair, width=12
        )
    
    # ===== EARS =====
    ear_size = 15
    draw.ellipse(
        [center_x - face_width - 8, center_y - 10,
         center_x - face_width + 8, center_y + 20],
        fill=skin,
        outline=(80, 60, 40),
        width=2
    )
    draw.ellipse(
        [center_x + face_width - 8, center_y - 10,
         center_x + face_width + 8, center_y + 20],
        fill=skin,
        outline=(80, 60, 40),
        width=2
    )
    
    # ===== EYES =====
    eye_y = center_y - 15
    eye_offset = 25
    left_eye_x = center_x - eye_offset
    right_eye_x = center_x + eye_offset
    
    # Eye whites
    if emotion in ["surprised", "shocked"]:
        eye_size = 18
    else:
        eye_size = 12
    
    if emotion in ["angry", "furious"]:
        # Angry - slit eyes
        draw.arc([left_eye_x - 15, eye_y - 8, left_eye_x + 15, eye_y + 8],
                180, 360, fill=(255, 255, 255), width=8)
        draw.arc([right_eye_x - 15, eye_y - 8, right_eye_x + 15, eye_y + 8],
                180, 360, fill=(255, 255, 255), width=8)
        # Pupils
        draw.ellipse([left_eye_x - 4, eye_y - 4, left_eye_x + 4, eye_y + 4], fill=(0, 0, 0))
        draw.ellipse([right_eye_x - 4, eye_y - 4, right_eye_x + 4, eye_y + 4], fill=(0, 0, 0))
    elif emotion in ["sad", "crying"]:
        # Sad - drooping eyes
        draw.ellipse([left_eye_x - eye_size, eye_y - eye_size, 
                     left_eye_x + eye_size, eye_y + eye_size],
                    fill=(255, 255, 255), outline=(0, 0, 0), width=2)
        draw.ellipse([right_eye_x - eye_size, eye_y - eye_size,
                     right_eye_x + eye_size, eye_y + eye_size],
                    fill=(255, 255, 255), outline=(0, 0, 0), width=2)
        # Pupils lower
        draw.ellipse([left_eye_x - 5, eye_y + 2, left_eye_x + 5, eye_y + 12], fill=(0, 0, 0))
        draw.ellipse([right_eye_x - 5, eye_y + 2, right_eye_x + 5, eye_y + 12], fill=(0, 0, 0))
        # Tear
        if emotion == "crying":
            draw.ellipse([left_eye_x - 3, eye_y + 15, left_eye_x + 3, eye_y + 25],
                        fill=(100, 150, 255))
    else:
        # Normal eyes
        # Whites
        draw.ellipse([left_eye_x - eye_size, eye_y - eye_size,
                     left_eye_x + eye_size, eye_y + eye_size],
                    fill=(255, 255, 255), outline=(0, 0, 0), width=2)
        draw.ellipse([right_eye_x - eye_size, eye_y - eye_size,
                     right_eye_x + eye_size, eye_y + eye_size],
                    fill=(255, 255, 255), outline=(0, 0, 0), width=2)
        # Pupils
        pupil_size = 6 if emotion in ["surprised", "shocked"] else 5
        draw.ellipse([left_eye_x - pupil_size, eye_y - pupil_size,
                     left_eye_x + pupil_size, eye_y + pupil_size], fill=(50, 30, 20))
        draw.ellipse([right_eye_x - pupil_size, eye_y - pupil_size,
                     right_eye_x + pupil_size, eye_y + pupil_size], fill=(50, 30, 20))
        # Eye shine (small white dots)
        draw.ellipse([left_eye_x - 2, eye_y - 4, left_eye_x + 2, eye_y], fill=(255, 255, 255))
        draw.ellipse([right_eye_x - 2, eye_y - 4, right_eye_x + 2, eye_y], fill=(255, 255, 255))
    
    # ===== EYEBROWS =====
    brow_y = eye_y - 20
    
    if emotion in ["angry", "furious"]:
        # Angry brows (V shape)
        draw.line([left_eye_x - 15, brow_y - 5, left_eye_x + 15, brow_y + 8],
                 fill=hair, width=5)
        draw.line([right_eye_x + 15, brow_y - 5, right_eye_x - 15, brow_y + 8],
                 fill=hair, width=5)
    elif emotion in ["sad", "crying"]:
        # Sad brows (^ shape)
        draw.line([left_eye_x - 15, brow_y + 5, left_eye_x + 15, brow_y - 8],
                 fill=hair, width=4)
        draw.line([right_eye_x + 15, brow_y + 5, right_eye_x - 15, brow_y - 8],
                 fill=hair, width=4)
    elif emotion in ["happy", "excited"]:
        # Happy brows (arched)
        draw.arc([left_eye_x - 15, brow_y - 5, left_eye_x + 15, brow_y + 10],
                180, 360, fill=hair, width=4)
        draw.arc([right_eye_x - 15, brow_y - 5, right_eye_x + 15, brow_y + 10],
                180, 360, fill=hair, width=4)
    elif emotion in ["surprised", "shocked"]:
        # Raised brows
        draw.arc([left_eye_x - 15, brow_y - 10, left_eye_x + 15, brow_y + 5],
                180, 360, fill=hair, width=4)
        draw.arc([right_eye_x - 15, brow_y - 10, right_eye_x + 15, brow_y + 5],
                180, 360, fill=hair, width=4)
    else:
        # Normal brows (straight)
        draw.line([left_eye_x - 12, brow_y, left_eye_x + 12, brow_y - 2],
                 fill=hair, width=3)
        draw.line([right_eye_x - 12, brow_y - 2, right_eye_x + 12, brow_y],
                 fill=hair, width=3)
    
    # ===== NOSE =====
    nose_y = center_y + 8
    draw.ellipse(
        [center_x - 6, nose_y - 3, center_x + 6, nose_y + 10],
        fill=tuple(max(0, c - 15) for c in skin),
        outline=(80, 60, 40),
        width=1
    )
    
    # ===== MOUTH (with speaking animation) =====
    mouth_y = center_y + 30
    
    if speaking_frame == 0:
        # Closed/neutral
        if emotion in ["happy", "excited"]:
            # Big smile
            draw.arc([center_x - 30, mouth_y - 15, center_x + 30, mouth_y + 15],
                    0, 180, fill=(200, 50, 50), width=5)
            # Teeth
            draw.arc([center_x - 25, mouth_y - 10, center_x + 25, mouth_y + 8],
                    0, 180, fill=(255, 255, 255), width=8)
        elif emotion in ["sad", "crying"]:
            # Frown
            draw.arc([center_x - 25, mouth_y - 5, center_x + 25, mouth_y + 15],
                    180, 360, fill=(200, 50, 50), width=4)
        elif emotion in ["angry", "furious"]:
            # Angry line
            draw.line([center_x - 20, mouth_y + 5, center_x + 20, mouth_y + 5],
                     fill=(200, 50, 50), width=5)
            # Small teeth
            for i in range(-15, 16, 8):
                draw.rectangle([center_x + i - 2, mouth_y - 3, center_x + i + 2, mouth_y + 5],
                              fill=(255, 255, 255))
        else:
            # Neutral small smile
            draw.arc([center_x - 15, mouth_y - 5, center_x + 15, mouth_y + 8],
                    0, 180, fill=(150, 50, 50), width=3)
    elif speaking_frame == 1:
        # Small opening
        draw.ellipse([center_x - 10, mouth_y - 3, center_x + 10, mouth_y + 10],
                    fill=(80, 40, 40), outline=(200, 50, 50), width=2)
    elif speaking_frame == 2:
        # Wide open (O shape)
        draw.ellipse([center_x - 15, mouth_y - 8, center_x + 15, mouth_y + 15],
                    fill=(80, 40, 40), outline=(200, 50, 50), width=2)
        # Teeth
        draw.rectangle([center_x - 10, mouth_y - 5, center_x + 10, mouth_y - 2],
                      fill=(255, 255, 255))
    else:
        # Medium open
        draw.ellipse([center_x - 12, mouth_y - 5, center_x + 12, mouth_y + 12],
                    fill=(80, 40, 40), outline=(200, 50, 50), width=2)


# TEST
if __name__ == "__main__":
    from PIL import Image, ImageDraw
    
    # Create test image
    img = Image.new('RGB', (1920, 1080), color=(30, 30, 50))
    draw = ImageDraw.Draw(img)
    
    # Draw different characters
    characters = [
        ("HERO", (0, 212, 255), "happy"),
        ("HEROINE", (255, 105, 180), "excited"),
        ("VILLAIN", (200, 30, 30), "angry"),
        ("CHILD", (255, 165, 0), "surprised"),
        ("OLD_MAN", (150, 150, 150), "sad"),
        ("NARRATOR", (255, 200, 0), "neutral"),
    ]
    
    positions = [(300, 900), (700, 900), (1100, 900),
                 (300, 500), (700, 500), (1100, 500)]
    
    for (char_type, color, emotion), pos in zip(characters, positions):
        x, y = pos
        draw_premium_character(
            draw=draw,
            center_x=x,
            ground_y=y,
            scale=0.5,
            character_type=char_type,
            color=color,
            emotion=emotion,
            speaking_frame=2,
        )
        # Label
        draw.text((x, y + 20), f"{char_type}\n[{emotion}]",
                 fill=(255, 255, 255), anchor='mm')
    
    img.save("premium_characters_preview.png")
    print("✅ Saved: premium_characters_preview.png")
    print("Opening...")
    os.startfile("premium_characters_preview.png")