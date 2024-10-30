# this script creates an svg vector file from a png image
# it has only been tested with black and white images as in pure black and pure white pixels
# other colors should work as well but has not been tested
# black pixels are ignored for memory efficiency

# the script is created by Claude from Anthropic as prompted by Diogo Aleixo
# https://github.com/sgm-17

# usage command: 
# python pixelArt_png2svg.py "input".png "output".svg




from PIL import Image
import numpy as np
from collections import defaultdict

class PixelGroup:
    def __init__(self, x, y, width, height, color):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.area = width * height

def find_horizontal_line(img_array, start_x, y, color, width, processed):
    """Find the length of a horizontal line of same-colored pixels."""
    x = start_x
    while x < width and not processed[y, x] and tuple(img_array[y][x]) == color:
        x += 1
    return x - start_x

def find_vertical_line(img_array, x, start_y, color, height, processed):
    """Find the length of a vertical line of same-colored pixels."""
    y = start_y
    while y < height and not processed[y, x] and tuple(img_array[y][x]) == color:
        y += 1
    return y - start_y

def find_rectangle(img_array, start_x, start_y, color, width, height, processed):
    """Find the largest possible rectangle of same-colored pixels."""
    # First find the maximum width
    rect_width = find_horizontal_line(img_array, start_x, start_y, color, width, processed)
    if rect_width == 0:
        return None
    
    # Then try to extend it vertically
    max_height = 1
    for y in range(start_y + 1, height):
        # Check if we can extend the rectangle down
        line_width = find_horizontal_line(img_array, start_x, y, color, start_x + rect_width, processed)
        if line_width < rect_width:
            break
        max_height += 1
    
    return PixelGroup(start_x, start_y, rect_width, max_height, color)

def optimize_shapes(shapes):
    """Combine adjacent shapes into paths where possible."""
    # Group shapes by color
    color_groups = defaultdict(list)
    for shape in shapes:
        color_groups[shape.color].append(shape)
    
    optimized_shapes = []
    
    for color, group in color_groups.items():
        # Sort shapes by position for better path creation
        group.sort(key=lambda s: (s.y, s.x))
        
        # Combine adjacent shapes
        current_path = []
        for shape in group:
            if not current_path:
                current_path.append(shape)
                continue
            
            # Check if shapes are adjacent
            last_shape = current_path[-1]
            if (last_shape.y == shape.y and 
                last_shape.x + last_shape.width == shape.x):
                # Merge horizontal shapes
                last_shape.width += shape.width
            elif (last_shape.x == shape.x and 
                  last_shape.width == shape.width and 
                  last_shape.y + last_shape.height == shape.y):
                # Merge vertical shapes
                last_shape.height += shape.height
            else:
                current_path.append(shape)
        
        optimized_shapes.extend(current_path)
    
    return optimized_shapes

def shape_to_path(shape):
    """Convert a shape to SVG path data."""
    x, y = shape.x, shape.y
    w, h = shape.width, shape.height
    
    # Create path data
    path = f"M {x} {y}"
    path += f" h {w}"  # right
    path += f" v {h}"  # down
    path += f" h {-w}"  # left
    path += "z"  # close path
    
    return path

def convert_png_to_svg(input_path, output_path):
    """Convert a PNG image to SVG with optimized shape detection and path generation."""
    # Load image and convert to RGBA
    img = Image.open(input_path).convert('RGBA')
    width, height = img.size
    img_array = np.array(img)
    
    # Keep track of processed pixels
    processed = np.zeros((height, width), dtype=bool)
    
    # Store all shapes
    shapes = []
    
    # Process each pixel
    for y in range(height):
        for x in range(width):
            if processed[y, x]:
                continue
                
            color = tuple(img_array[y][x])
            
            # Skip black or transparent pixels
            if color[3] == 0 or (color[0] == 0 and color[1] == 0 and color[2] == 0):
                processed[y, x] = True
                continue
            
            # Try to find a rectangle
            rect = find_rectangle(img_array, x, y, color, width, height, processed)
            if rect:
                shapes.append(rect)
                # Mark all pixels in the rectangle as processed
                processed[rect.y:rect.y+rect.height, rect.x:rect.x+rect.width] = True
                continue
            
            # If no rectangle, try vertical line
            v_length = find_vertical_line(img_array, x, y, color, height, processed)
            if v_length > 1:
                shapes.append(PixelGroup(x, y, 1, v_length, color))
                processed[y:y+v_length, x] = True
                continue
            
            # If no vertical line, try horizontal line
            h_length = find_horizontal_line(img_array, x, y, color, width, processed)
            if h_length > 1:
                shapes.append(PixelGroup(x, y, h_length, 1, color))
                processed[y, x:x+h_length] = True
                continue
            
            # Single pixel
            shapes.append(PixelGroup(x, y, 1, 1, color))
            processed[y, x] = True
    
    # Optimize shapes
    optimized_shapes = optimize_shapes(shapes)
    
    # Generate SVG
    svg_content = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">'
    ]
    
    # Group shapes by color to reduce redundant style information
    color_groups = defaultdict(list)
    for shape in optimized_shapes:
        color_groups[shape.color].append(shape)
    
    # Create paths for each color group
    for color, group in color_groups.items():
        hex_color = '#{:02x}{:02x}{:02x}'.format(color[0], color[1], color[2])
        opacity = color[3] / 255
        
        # Combine all shapes of the same color into one path element
        path_data = ' '.join(shape_to_path(shape) for shape in group)
        path = f'<path d="{path_data}" fill="{hex_color}"'
        if opacity < 1:
            path += f' opacity="{opacity}"'
        path += '/>'
        svg_content.append(path)
    
    svg_content.append('</svg>')
    
    # Write SVG file
    with open(output_path, 'w') as f:
        f.write('\n'.join(svg_content))

# Example usage
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python script.py input.png output.svg")
        sys.exit(1)
    
    convert_png_to_svg(sys.argv[1], sys.argv[2])