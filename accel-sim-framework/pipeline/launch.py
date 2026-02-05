#!/usr/bin/env python3

import os
import yaml
from pathlib import Path


DIR_PATH = Path(__file__).resolve().parent
SIM_CONFIGS_DIR = f"{DIR_PATH}/configs"
PIPELINE_CONFIG_FILE = f"{DIR_PATH}/pipeline.yaml"

trace_lookup = {}

def parse_pipeline_config():
    config = {}
    with open(PIPELINE_CONFIG_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        config["results_dir"] = os.path.expandvars(config["results_dir"])
        for dest in ["trace_lookup", "results_dir"]:
            config[dest] = os.path.expandvars(config[dest])
        for dest in config["config_destinations"]:
            config["config_destinations"][dest] = os.path.expandvars(config["config_destinations"][dest])
        for i in range(len(config["instances"])):
            config["instances"][i] = config["instances"][i].replace("-", "_")
        return config

def parse_trace_lookup(t_path):
    global trace_lookup
    with open(t_path, "r", encoding="utf-8") as f:
        trace_lookup = yaml.safe_load(f)
        for trace in trace_lookup:
            trace_lookup[trace] = os.path.expandvars(trace_lookup[trace])

def prepare_instance(instance, dest):
    if not os.path.exists(os.path.join(SIM_CONFIGS_DIR, instance)):
        print(f"Skipping {instance} due to missing configuration-folder")
        return False
    os.chdir(f"{SIM_CONFIGS_DIR}/{instance}")
    src_dir = os.path.join(SIM_CONFIGS_DIR, instance)

    if not os.path.exists(f"{SIM_CONFIGS_DIR}/{instance}/gpgpusim.config"):
        print(f"Skipping {instance} due to missing file: gpgpusim.config")
        return False
    elif not os.path.exists(f"{SIM_CONFIGS_DIR}/{instance}/trace.config"):
        print(f"Skipping {instance} due to missing file: trace.config")
        return False

    os.makedirs(dest["gpgpusim"], exist_ok=True)
    os.chdir(dest["gpgpusim"])
    gpgpusim_dest = dest["gpgpusim"] + "/" + instance
    if os.path.exists(gpgpusim_dest):
        os.system(f"rm -rf {instance}")
    os.makedirs(gpgpusim_dest)
    

    os.makedirs(dest["trace"], exist_ok=True)
    os.chdir(dest["trace"])
    trace_dest = dest["trace"] + "/" + instance
    if os.path.exists(trace_dest):
        os.system(f"rm -rf {instance}")
    os.makedirs(trace_dest)
    

    os.system(f"cp {src_dir}/gpgpusim.config {gpgpusim_dest}/")
    os.system(f"cp {src_dir}/*.icnt {gpgpusim_dest}/ > /dev/null 2>&1")
    os.system(f"cp {src_dir}/*.xml {gpgpusim_dest}/ > /dev/null 2>&1")
    os.system(f"cp {src_dir}/trace.config {trace_dest}/")


    cfgs_yml = os.path.expandvars("$ACCEL_SIM/" \
        "util/job_launching/configs/define-standard-cfgs.yml"
    )
    cfgs = {}
    with open(cfgs_yml, "r") as f:
        cfgs = yaml.safe_load(f)
    
    if instance not in cfgs:
        cfgs[instance] = {"base_file": f"{gpgpusim_dest}/gpgpusim.config"}
        with open(cfgs_yml, "a") as f:
            f.write(f"\n\n{instance}:\n")
            f.write(f"    base_file: \"{gpgpusim_dest}/gpgpusim.config\"")
    else:
        lines = []
        with open(cfgs_yml, "r") as f:
            found = False
            for line in f:
                if found:
                    lines.append(f"    base_file: \"{gpgpusim_dest}/gpgpusim.config\"\n")
                    found = False
                    continue
                else:
                    lines.append(line)
                
                if instance in line:
                    found = True
        with open(cfgs_yml, "w") as f:
            for line in lines:
                f.write(line)

    os.chdir(DIR_PATH)
    return True


def build_command(config, benchmark, instance=None, aggregate=False):
    cmd = []
    exec_path = os.path.expandvars("$ACCEL_SIM/util/job_launching/run_simulations.py")
    cmd.append(exec_path)
    cmd.append(f"-l {config['launcher']}")
    cmd.append(f"-M {config['job_mem']}")
    cmd.append(f"-B {benchmark}")
    if aggregate:
        c_line = f"-C "
        extra_configs = "-".join(config["extra_configs"])
        for inst in config["instances"]:
            c_line += f"{inst}-{extra_configs},"
        cmd.append(c_line[:-1])
        instance = '$(date +"%Y_%m_%d__%H_%M")'
    else:
        cmd.append(f"-C {instance}-{'-'.join(config['extra_configs'])}")
    cmd.append(f"-T {trace_lookup[benchmark.split(':')[0]]}")
    cmd.append(f"-N {config['name_prefix']}-{instance}")
    cmd.append(f"-r {config['results_dir']}/{instance}")
    if config["override_names"]:
        cmd.append("-o True")
    return cmd


def export_commands(commands, path):
    with open(path, 'w') as f:
        f.write('#!/usr/bin/env bash\n\n')
        for command in commands:
            cmd = command[0] + ' \\\n'
            for i in range(1, len(command)):
                cmd += '\t' + command[i] + ' \\\n'
            f.write(cmd[:-3] + '\n\n')
    os.system(f"chmod +x {path}")


def ensure_dirs_present(dirs):
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def main():
    pipeline_config = parse_pipeline_config()
    parse_trace_lookup(pipeline_config['trace_lookup'])
    ensure_dirs_present([pipeline_config["results_dir"]])
    commands = []
    
    if pipeline_config["aggregate"]:
        for benchmark in pipeline_config["benchmarks"]:
            for inst in pipeline_config["instances"]:
                if not prepare_instance(inst, pipeline_config["config_destinations"]):
                    pipeline_config["instances"].remove(inst)
            commands.append(build_command(config=pipeline_config, benchmark=benchmark, aggregate=True))
    else:
        for inst in pipeline_config["instances"]:
            for benchmark in pipeline_config["benchmarks"]:
                if not prepare_instance(inst, pipeline_config["config_destinations"]): continue
                commands.append(build_command(config=pipeline_config, instance=inst))

    export_path = os.path.join(pipeline_config['results_dir'], 'launch.sh')
    export_commands(commands, export_path)

    print("\n\nPipeline creation complete")
    print(f"Script to start simulator-instances written to: \n - {export_path}")


    while True:
        ans = input("\nStart instances now (y/n): ").strip() 
        if ans.casefold() == "y".casefold():
            os.system(f"bash {export_path}")
            print("Command executed, verify by using the ps command in the terminal.")
            break
        elif ans.casefold() == "n".casefold():
            break
        else:
            print("Invalid input, please write y or n.")

main()
