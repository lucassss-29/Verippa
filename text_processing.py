import re
import os

def clean_verilog_file(input_filename, output_filename):
    if not os.path.exists(input_filename):
        print(f"Error: {input_filename} not found.")
        return

    with open(input_filename, 'r') as f:
        content = f.read()

    # Regex breakdown:
    # \bmodule\b -> Matches the whole word 'module'
    # .*?        -> Matches everything in between (non-greedy)
    # endmodule  -> Matches the closing term
    # re.DOTALL  -> Essential! Allows the '.' to match newlines
    pattern = re.compile(r'\bmodule\b.*?endmodule', re.DOTALL)

    # Find all matches
    matches = pattern.findall(content)

    if matches:
        # Join the modules with two newlines for clean separation
        cleaned_output = "\n\n".join(matches)
        
        with open(output_filename, 'w') as f:
            f.write(cleaned_output)
            
        print(f"Extracted {len(matches)} modules to {output_filename}")
        print("Dropped all text outside the module/endmodule blocks.")
        return True
    else:
        print("No modules found in the file.")
        return False

# Run the script
# clean_verilog_file("source.v", "cleaned_design.v")

def clean_testbench_file(input_filename, output_filename):
    if not os.path.exists(input_filename):
        print(f"Error: {input_filename} not found.")
        return

    with open(input_filename, 'r') as f:
        content = f.read()

        #Check if `timescale is in the content
        if "`timescale" in content:
            print("Case 1: `timescale found in the testbench.")
            # Clean from timescale to endmodule
            pattern = re.compile(r"(`timescale.*endmodule)", re.DOTALL)

            match = pattern.search(content)

            if match:
                cleaned_content = match.group(1)
                with open(output_filename, 'w') as f:
                    f.write(cleaned_content)
                print(f"Cleaned testbench saved to {output_filename}")
                return True
            else:
                print("Could not find a valid block starting with `timescale and ending with endmodule.")
                return False
        else:
            print("Case 2: `timescale not found in the testbench.")
            result = clean_verilog_file(input_filename, output_filename)
            if result:
                # Add timescale at the beginning if not found
                timescale="`timescale 1ns/1ps"
                with open(input_filename, 'r') as f:
                    lines = f.readlines()

                lines.insert(0, f"{timescale}\n")

                with open(output_filename, 'w') as f:
                    f.writelines(lines)
                print(f"Added {timescale} to the beginning of {output_filename}.")

                return True
            else:
                print("Failed to clean the testbench file.")
                return False
            
