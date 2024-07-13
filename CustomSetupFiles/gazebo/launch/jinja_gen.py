#!/usr/bin/env python3

import jinja2
import argparse
import os
import shutil
import fnmatch
import json
import numpy as np


def get_file_contents(filepath):
    with open(filepath, 'rb') as f:
        return f.read()

def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def read_jinja_parameters_from_file(filepath):
    if not filepath:
        return {}
    if not os.path.exists(filepath):
        return {}
    with open(filepath) as f:
        data = json.load(f)
        return data
    return {}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', help="file that the sdf file should be generated from")
    parser.add_argument('env_dir')
    parser.add_argument('--cf_id', default=0, help="Crazyflie unique identifier number")
    parser.add_argument('--cffirm_udp_port', default=19950, help="Crazyflie Firmware UDP port")
    parser.add_argument('--cflib_udp_port', default=19850, help="Crazyflie python library UDP port")
    parser.add_argument('--cf_name', default="cf", help="Serial device for FMU")
    parser.add_argument('--output-file', help="sdf output file")
    parser.add_argument('--stdout', action='store_true', default=False, help="dump to stdout instead of file")
    # parser.add_argument('--override_parameters_json_path', default='', help="json file with variables to override jinja parameters")
    args = parser.parse_args()
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(args.env_dir))
    template = env.get_template(os.path.relpath(args.filename, args.env_dir))

    d = {'np': np, \
         'cf_id': args.cf_id, \
         'cffirm_udp_port': args.cffirm_udp_port, \
         'cflib_udp_port': args.cflib_udp_port, \
         'cf_name': args.cf_name}

    # override_params_path = args.override_parameters_json_path
    # if not override_params_path:
    #     override_params_path = args.env_dir + "/resources/px4_gazebo_jinja_parameters.json"

    # parameters_from_json_file = read_jinja_parameters_from_file(override_params_path)
    # d.update(parameters_from_json_file)
    result = template.render(d)

    if args.stdout:
        print(result)

    else:
        if args.output_file:
            filename_out = args.output_file
        else:
            if not args.filename.endswith('.sdf.jinja'):
                raise Exception("ERROR: Output file can only be determined automatically for " + \
                                "input files with the .sdf.jinja extension")
            filename_out = args.filename.replace('.sdf.jinja', '.sdf')
            assert filename_out != args.filename, "Not allowed to overwrite template"

        # Overwrite protection mechanism: after generation, the file will be copied to a "last_generated" file.
        # In the next run, we can check whether the target file is still unmodified.
        filename_out_last_generated = filename_out + '.last_generated'

        if os.path.exists(filename_out) and os.path.exists(filename_out_last_generated):
            # Check whether the target file is still unmodified.
            if get_file_contents(filename_out).strip() != get_file_contents(filename_out_last_generated).strip():
                raise Exception("ERROR: generation would overwrite changes to `{}`. ".format(filename_out) + \
                                "Changes should only be made to the template file `{}`. ".format(args.filename) + \
                                "Remove `{}` ".format(os.path.basename(filename_out)) + \
                                "(after extracting your changes) to disable this overwrite protection.")

        with open(filename_out, 'w') as f_out:
            print(('{:s} -> {:s}'.format(args.filename, filename_out)))
            f_out.write(result)

        # Copy the contents to a "last_generated" file for overwrite protection check next time.
        shutil.copy(filename_out, filename_out_last_generated)