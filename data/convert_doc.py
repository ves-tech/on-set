import json
from bs4 import BeautifulSoup
import re
import os
import urllib.parse
import csv

def load_vfx_type_mapping(csv_path):
    mapping = {}
    if not os.path.exists(csv_path):
        print(f"Warning: CSV path {csv_path} does not exist.")
        return mapping
        
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            # Headers: Number, Title, [Types...]
            type_headers = headers[2:]
            
            for row in reader:
                if not row: continue
                number = row[0].strip()
                if not number: continue
                
                types = []
                # Check each type column
                for i, cell in enumerate(row[2:]):
                    if cell.strip(): # If cell is not empty, it belongs to this type
                        types.append(type_headers[i].strip())
                
                if types:
                    mapping[number] = types
    except Exception as e:
        print(f"Error reading CSV: {e}")
        
    return mapping

def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()

def parse_directory_tree(lines):
    root = []
    stack = [] # tuple of (level, node)
    
    for line in lines:
        line = line.replace('\xa0', ' ') # Replace non-breaking space
        
        # Regex to capture lead
        # Matches any sequence of │, ├, └, ─, or space
        match = re.match(r'^([│├└─\s]+)(.*)', line)
        if not match:
            continue
            
        prefix = match.group(1)
        name = match.group(2).strip()
        
        if not name: continue
        
        # Calculate level.
        # "│   " is 4 chars.
        level = len(prefix) // 4
        
        node = {
            "name": name,
            "children": []
        }
        
        # Stack logic
        if not stack:
            # First item
            root.append(node)
            stack.append((level, node))
        else:
            # Find parent: Pop items from stack that are at same or deeper level
            while stack and stack[-1][0] >= level:
                stack.pop()
            
            if stack:
                # Add to the node at the top of the stack (parent)
                stack[-1][1]["children"].append(node)
                stack.append((level, node))
            else:
                # Top level sibling
                root.append(node)
                stack.append((level, node))
                
    return root

def parse_google_doc_html(html_path, output_css_path=None):
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    # Extract Version and Date
    version = "Unknown"
    publish_date = "Unknown"
    
    # Look for the version string in the first few paragraphs
    # Format appears to be: Version: 1.0.0 - 2026-02-06
    import re
    version_pattern = re.compile(r"Version:\s*([\d\.]+)\s*-\s*([\d-]+)")
    
    for p in soup.find_all('p', limit=20):
        text = p.get_text().strip()
        match = version_pattern.search(text)
        if match:
            version = match.group(1)
            publish_date = match.group(2)
            break
            
    print(f"Found Version: {version}, Date: {publish_date}")

    # Extract styles
    style_content = ""
    for style in soup.find_all("style"):
        style_content += style.get_text()
    
    if style_content and output_css_path:
        # Write to requested location
        os.makedirs(os.path.dirname(output_css_path), exist_ok=True)
        with open(output_css_path, "w", encoding="utf-8") as f:
            f.write(style_content)
            print(f"Extracted styles to {output_css_path}")

    # Structure
    output = {
        "Introduction": [],
        "Scope Definitions": [],
        "Data Sets": [],
        "Directory Structure": [], # Will now just be a placeholder or empty in main data
        "Reference Docs": [],
        "Feedback": []
    }
    
    current_h1_obj = None
    current_h2_obj = None
    
    # Accumulator for directory lines
    directory_lines = []
    in_tree = False
    
    # We iterate through all relevant elements in order
    # Note: re.compile matches tags
    elements = soup.find_all(re.compile(r'^h[1-2]|^table|^p|^ul|^ol'))
    
    # Helper to remove comments before text extraction
    def remove_comments(tag):
        for a_tag in tag.find_all('a', href=True):
            if a_tag['href'].startswith('#cmnt'):
                a_tag.decompose()

    for el in elements:
        # Pre-clean comments from the element before any processing
        # This ensures titles, tables, and paragraphs all get cleaned.
        remove_comments(el)
        
        text = clean_text(el.get_text(separator=' ', strip=True))
        
        # Check for Directory Structure (ASCII Tree)
        # We collect these lines separately now
        if any(char in text for char in ['│', '├', '└']) and len(text) > 2:
             # We want the raw text with indentation, so use el.get_text without strip=True for logic,
             # but actually our parse function expects just lines. 
             # Let's trust el.get_text() preserves enough. 
             # Actually, clean_text strips whitespace. We need the raw leading whitespace/chars.
             raw_text = el.get_text(separator=' ', strip=False)
             # Also replace non-breaking spaces early to be safe
             raw_text = raw_text.replace('\xa0', ' ')
             if any(char in raw_text for char in ['│', '├', '└']):
                 in_tree = True
                 # If we encounter tree lines, ensure we stop adding to Reference Docs (or any previous section)
                 # This prevents empty lines or artifacts within the tree from falling back into the previous section.
                 if current_h1_obj and current_h1_obj.get("title") == "Reference Docs":
                     current_h1_obj = None 
                 directory_lines.append(raw_text)
                 continue # Skip adding to normal output

        if el.name == 'h1':
            in_tree = False
            if text in ["Introduction", "Scope Definitions", "17. Reference Documents", "Feedback", "VFX Types"] or "Directory Structure" in text:
                if "17." in text: # specific check for Ref docs to normalize key if needed, or just use text
                     current_h1_obj = {"title": "Reference Docs", "special": True}
                elif "Directory Structure" in text:
                     current_h1_obj = {"title": "Directory Structure", "special": True}
                else:
                     current_h1_obj = {"title": text, "special": True}
                
                if current_h1_obj["title"] not in output:
                    output[current_h1_obj["title"]] = []
                current_h2_obj = None
            else:
                current_h1_obj = {
                    "title": text,
                    "subsections": []
                }
                output["Data Sets"].append(current_h1_obj)
                current_h2_obj = None
                
        elif el.name == 'h2':
            if current_h1_obj and not current_h1_obj.get("special"):
                current_h2_obj = {
                    "title": text,
                    "items": []
                }
                current_h1_obj["subsections"].append(current_h2_obj)
            else:
                current_h2_obj = None 

        elif el.name in ['p', 'ul', 'ol']:
            if current_h1_obj and current_h1_obj.get("special"):
                 if in_tree and current_h1_obj["title"] == "Directory Structure":
                      continue
                      
                 # Handle special sections content (Intro, Scope, Ref Docs)
                 target_list = output[current_h1_obj["title"]]
                 
                 # Strip all attributes (class, style, etc) except href/src to ensure vanilla HTML
                 # This removes Google Doc formatting completely
                 def strip_attrs(tag):
                     attrs = dict(tag.attrs)
                     for attr in attrs:
                         if attr not in ['href', 'src']:
                             del tag[attr]

                 strip_attrs(el)
                 for child in el.find_all(True):
                     strip_attrs(child)
                 
                 # For Reference Docs, we want to keep links working.
                 # The 'clean_text' might strip some html if applied too aggressively, 
                 # but here we use decode_contents which preserves tags.
                 
                 for span in el.find_all('span'):
                    span.unwrap()

                 # Clean up Google Redirects and Comment Links
                 for a_tag in el.find_all('a', href=True):
                     href = a_tag['href']
                     
                     # Remove Google Doc comment links (e.g. #cmnt1) and their content (e.g. [a])
                     if href.startswith('#cmnt'):
                         a_tag.decompose()
                         continue

                     if href.startswith('https://www.google.com/url'):
                         # Extract 'q' parameter
                         match = re.search(r'[?&]q=([^&]+)', href)
                         if match:
                             real_url = match.group(1)
                             # URL decode if needed (simple approximation or import standard lib)
                             # Assuming standard unquote isn't imported, let's keep it simple or import urllib.parse at top.
                             # Actually standard library is best.
                             real_url = urllib.parse.unquote(real_url)
                             a_tag['href'] = real_url

                 # Special replacement for the embedded image in Introduction
                 if current_h1_obj["title"] == "Introduction":
                     for img in el.find_all('img'):
                         img['src'] = "https://ves-on-set-data.org/dashboard/sankey_vis.jpg"
                         # Wrap the image in a link to the visualization page
                         new_a = soup.new_tag("a", href="https://ves-on-set-data.org/dashboard/vis.html")
                         img.wrap(new_a)

                 content = el.decode_contents().strip()
                 
                 # Check for junk content to ignore/stop
                 text_content = el.get_text().strip()
                 if "Blank VFX Vendor Specs" in text_content or text_content == ".":
                     continue
                 
                 # Stop capturing if we hit the internal notes section starting with "JF -"
                 if "JF -" in text_content:
                     current_h1_obj = None # Stop capturing for this section
                     continue
                 
                 # Also stop if we see "Directory Structure" title as plain text (if it wasn't caught as H1)
                 if "Directory Structure" in text_content and len(text_content) < 40:
                     if current_h1_obj and current_h1_obj.get("title") == "Reference Docs":
                         current_h1_obj = None
                         continue

                 # Special deduplication for Scope Definitions:
                 # If we are in Scope Definitions, and the text matches a Key or Value from a previously parsed table, skip it.
                 if current_h1_obj and current_h1_obj["title"] in ["Scope Definitions", "VFX Types"]:
                     is_duplicate = False
                     # Iterate over existing items in this section (which might include the Table parsed earlier)
                     for item in target_list:
                         for k, v in item.items():
                             if k == "html": continue
                             # Check if text matches Key (exact)
                             if text_content == k:
                                 is_duplicate = True
                                 break
                             # Check if text is part of Value (substring)
                             # We use strict equality for Key, but substring for Value to catch split paragraphs.
                             # Safety check: text should be reasonably long to avoid false positives with short words.
                             if isinstance(v, str):
                                 clean_v = v.replace('\n', ' ').strip()
                                 content_check = text_content.replace('\n', ' ').strip()
                                 if content_check == clean_v:
                                     is_duplicate = True
                                     break
                                 # Partial match buffer
                                 if len(content_check) > 10 and content_check in clean_v:
                                      is_duplicate = True
                                      break
                                      
                         if is_duplicate: break
                     
                     if is_duplicate:
                         continue

                 if content:
                    target_list.append({"html": f"<{el.name}>{content}</{el.name}>"})

        elif el.name == 'table':
            # Helper to remove comments before text extraction
            def remove_comments(tag):
                for a_tag in tag.find_all('a', href=True):
                    if a_tag['href'].startswith('#cmnt'):
                        a_tag.decompose()

            # Parse table
            table_data = {}
            rows = el.find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 2:
                    # Clean comments from both columns
                    remove_comments(cols[0])
                    remove_comments(cols[1])

                    key = clean_text(cols[0].get_text(separator=' ', strip=True))
                    
                    ul = cols[1].find('ul')
                    if ul:
                        value = sorted(list(set([clean_tag(li.get_text(separator=' ', strip=True)) for li in ul.find_all('li')])))
                    else:
                        value = clean_text(cols[1].get_text(separator=' ', strip=True))
                        # If key is Creator/Consumer, run clean_tag on single value too provided it's string
                        if key in ["Creator", "Consumer"] and isinstance(value, str):
                            value = [clean_tag(value)]
                    
                    if key:
                        table_data[key] = value

            if table_data:
                # Add to structure
                if current_h1_obj:
                    if current_h1_obj.get("special"):
                        # Add directly to Intro/Scope/Ref list
                        output[current_h1_obj["title"]].append(table_data)
                    elif current_h2_obj:
                        # Add to subsection
                        current_h2_obj["items"].append(table_data)
                    else:
                        # Add to root of H1 (orphaned table?)
                        if not current_h1_obj["subsections"]:
                             current_h1_obj["subsections"].append({"title": "General", "items": []})
                        current_h1_obj["subsections"][-1]["items"].append(table_data)

    # Post-process: Inject VFX Types from CSV mapping
    # We assume the CSV path is predictable or passed in globally, but for now let's look for it in the same dir as input
    # actually getting it from args would be cleaner, but let's assume standard location for now:
    # "data/on-set-title-type-mapping - titles.csv"
    
    # Try to find the CSV file relative to the input file or current working dir
    # This is a bit hacky relying on hardcoded name but fits the immediate request
    csv_name = "on-set-title-type-mapping - titles.csv"
    csv_path = os.path.join(os.path.dirname(html_path), csv_name)
    
    vfx_mapping = load_vfx_type_mapping(csv_path)
    
    if vfx_mapping:
        print(f"Loaded {len(vfx_mapping)} VFX type mappings.")
        
        # Helper to find number in title
        def extract_number(title):
            # Matches "1.", "1.1", "10.1" etc at start
            match = re.match(r'^(\d+(\.\d+)*)', title)
            return match.group(1) if match else None

        for h1 in output["Data Sets"]:
            h1_number = extract_number(h1["title"])
            
            for h2 in h1["subsections"]:
                h2_number = extract_number(h2["title"])
                
                # Determine which number to use for lookup. 
                # H2 is more specific, but maybe we want to fall back to H1?
                # The CSV seems to have specific rows for 1.1, 1.2 etc.
                # Let's try matching H2 first.
                
                target_types = []
                if h2_number and h2_number in vfx_mapping:
                    target_types = vfx_mapping[h2_number]
                elif h1_number and h1_number in vfx_mapping:
                     target_types = vfx_mapping[h1_number]
                
                if target_types:
                    for item in h2["items"]:
                        item["VFXTypes"] = target_types

    # Post-process Merge HTML blocks
    for section in ["Introduction", "Reference Docs", "Feedback", "Directory Structure", "VFX Types"]:
        if output.get(section): # Safely get
            # If it's a list of dictionaries (from tables), we might want to keep it as is or convert to HTML
            # The current logic for special sections assumes they contain {"html": "..."} or tables.
            # Let's see if we should merge them or keep them as structured data.
            # For VFX Types, it might be better to keep it structured if it's a table.
            
            # If the section contains only tables (dicts with keys other than 'html'), let's NOT merge into one big div yet,
            # or handle it in app.js.
            # Actually, the existing logic for Intro/Scope/Ref assumes they are lists of blocks.
            
            if section == "VFX Types":
                continue # Keep structured for now to allow better rendering
                
            merged_html = f"<div class='text-block-{section.lower().replace(' ', '-')}'>" + "".join([str(x["html"]) for x in output[section] if "html" in x]) + "</div>"
            output[section] = [{"html": merged_html}]
            
    if not output.get("Directory Structure"):
        output["Directory Structure"] = []
    output["Directory Structure"].append({"type": "tree_view"})

    data = {
        "version": version,
        "publishDate": publish_date,
        "Introduction": output["Introduction"],
        "Scope Definitions": output["Scope Definitions"],
        "VFX Types": output.get("VFX Types", []),
        "Data Sets": output["Data Sets"],
        "Directory Structure": output["Directory Structure"],
        "Reference Docs": output["Reference Docs"],
        "Feedback": output["Feedback"]
    }
    
    return data, directory_lines

def clean_tag(tag):
    # 1. Basic cleaning
    tag = clean_text(tag)
    # Remove trailing/leading punctuation
    tag = tag.strip('.,;:')
    
    # 2. Fix specific typos/variations found in analysis
    corrections = {
        "Previz vendo rs": "Previz vendor",
        "Previz vendor s": "Previz vendor",
        "Sounds department": "Sound department",
        "Stunts department": "Stunt department",
        "Digital intermediate (DI) facility": "DI Vendor",
        "Digital intermediateI vendor": "DI Vendor",
        "Dailies and Digital Intermediate vendor": "Dailies and DI Vendor",
        "Dailies and DI vendor": "Dailies and DI Vendor",
        "DIT": "Digital Imaging Technician",
        "Digital imaging Technician (DIT)": "Digital Imaging Technician",
        "Script supervisor": "Script Supervisor",
        "Assistant directory (AD)": "Assistant Director",
        "First AD": "Assistant Director",
        "AD department": "Assistant Director",
        "Motion capture team": "Motion Capture Vendor",
    }
    
    if tag in corrections:
        tag = corrections[tag]

    # 3. Standardization (Title Case)
    # Capitalize first letter of each word, lower the rest (except known acronyms)
    # Ideally use string.capwords but consistent casing is key.
    # Simple Title Case:
    words = tag.split()
    normalized_words = []
    for w in words:
        if w.upper() in ["VFX", "DI", "GPS", "LED", "UPM", "SFX", "AD"]:
            normalized_words.append(w.upper())
        else:
            normalized_words.append(w.capitalize())
    tag = " ".join(normalized_words)

    # 4. Singularize (Naive)
    # If ends in 's' (and isn't 'lens', 'process', etc), drop 's'
    # Check against known singles? 
    # For now, simplistic: if "Vendors" -> "Vendor", "Departments" -> "Department"
    if tag.endswith("s"):
        if tag.endswith("Vendors"):
            tag = tag[:-1]
        elif tag.endswith("Departments"):
            tag = tag[:-1]
        elif tag.endswith("Performers"):
            tag = tag[:-1]
        elif tag.endswith("Teams"):
            tag = tag[:-1]
            
    return tag

import sys
import argparse
import urllib.request
import yaml

def download_google_doc(doc_id, output_path):
    url = f"https://docs.google.com/document/d/{doc_id}/export?format=html"
    print(f"Downloading Google Doc: {doc_id}...")
    try:
        with urllib.request.urlopen(url) as response:
            with open(output_path, 'wb') as f:
                f.write(response.read())
        print(f"Successfully downloaded to {output_path}")
        return True
    except Exception as e:
        print(f"Error downloading document: {e}")
        return False

if __name__ == "__main__":
    import os
    
    parser = argparse.ArgumentParser(description="Convert Google Doc HTML export to JSON data for On-Set Dashboard.")
    parser.add_argument("--doc-id", help="Google Doc ID to download automatically (e.g. 13TsptYa5uNO52btOw1nat1cLSBG88t27W3BXHBZPvoc)")
    parser.add_argument("--input", default="data/doc_export.html", help="Input HTML file path (default: data/doc_export.html)")
    parser.add_argument("--output", default="data/data.json", help="Output JSON file path (default: data/data.json)")
    
    args = parser.parse_args()
    
    input_file = args.input
    output_file = args.output
    
    # If Doc ID is provided, download it first
    if args.doc_id:
        # Ensure the directory for the input file exists if it's a path
        input_dir = os.path.dirname(input_file)
        if input_dir and not os.path.exists(input_dir):
            os.makedirs(input_dir)

        if download_google_doc(args.doc_id, input_file):
            print("Download complete. Proceeding to conversion...")
        else:
            print("Download failed. Aborting.")
            sys.exit(1)
            
    # Adjust paths to be robust
    # Convert to absolute paths for consistency, especially for CSS output calculation
    if not os.path.isabs(input_file):
        input_file = os.path.abspath(input_file)
    if not os.path.isabs(output_file):
        output_file = os.path.abspath(output_file)
        
    # Determine CSS output path relative to the output JS file's directory
    css_output_file = os.path.join(os.path.dirname(output_file), "../dashboard/doc_styles.css")
    
    print(f"Parsing {input_file}...")
    try:
        # Now returns tuple: (json_data, directory_lines)
        result = parse_google_doc_html(input_file, css_output_file)
        
        # Determine valid result
        if isinstance(result, tuple):
            json_data, directory_lines = result
        else:
            # Fallback if function signature didn't update as expected (safety)
            json_data = result
            directory_lines = []
        
        # Parse directory lines into tree structure
        if directory_lines:
            print(f"Found {len(directory_lines)} directory structure lines. Parsing tree...")
            directory_tree = parse_directory_tree(directory_lines)
            
            print(f"Found {len(directory_lines)} directory structure lines. Parsing tree...")
            directory_tree = parse_directory_tree(directory_lines)

            # Save to YAML file (for user consumption)
            def to_list_based_structure(nodes):
                if not nodes:
                    return []
                
                result_list = []
                for node in nodes:
                    name = node['name']
                    children = node.get('children', [])
                    
                    if children:
                        # Recursively get list of children
                        result_list.append({ name: to_list_based_structure(children) })
                    else:
                        # Leaf node: Just the name string
                        result_list.append(name)
                return result_list

            # The top level directory_tree is a list of Roots.
            # We want the output to be a Dict of Roots to Lists, OR a List of Roots?
            # User example: "app: ..." (Dict at top).
            # My data has multiple roots. So I should probably return a Dict merging them.
            
            final_yaml_data = {}
            for root in directory_tree:
                name = root['name']
                children = root.get('children', [])
                # The root's children should be a list
                final_yaml_data[name] = to_list_based_structure(children)
            
            yaml_output_file = os.path.join(os.path.dirname(output_file), "directory_structure.yaml")
            
            # Generate YAML string
            yaml_content = yaml.dump(final_yaml_data, default_flow_style=False, sort_keys=False, allow_unicode=True)

            with open(yaml_output_file, 'w', encoding='utf-8') as f:
                f.write(yaml_content)
            print(f"Directory structure saved to {yaml_output_file}")
            
            # Write directory tree as pure JSON (no JS wrapper)
            dir_output_file = os.path.join(os.path.dirname(output_file), "directory_data.json")
            with open(dir_output_file, 'w', encoding='utf-8') as f:
                f.write(json.dumps(directory_tree, indent=4))
            print(f"Directory data saved to {dir_output_file}")
            
        # Ensure the output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Write main JSON file (pure JSON, no JS wrapper)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(json_data, indent=4))
            
        
        print(f"Successfully converted to {output_file}")
        
    except FileNotFoundError:
        print(f"Error: {input_file} not found. Make sure you downloaded the HTML export.")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
