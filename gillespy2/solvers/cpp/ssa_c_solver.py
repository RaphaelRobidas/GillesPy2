from gillespy2.core import gillespyError, GillesPySolver, log
from gillespy2.solvers.utilities import solverutils as cutils
import signal  # for solver timeout implementation
import os  # for getting directories for C++ files
import shutil   # for deleting/copying files
import subprocess  # for calling make and executing c solver
import tempfile  # for temporary directories

GILLESPY_PATH = os.path.dirname(os.path.abspath(__file__))
GILLESPY_CPP_SSA_DIR = os.path.join(GILLESPY_PATH, 'c_base/ssa_cpp_solver')
MAKE_FILE = os.path.dirname(os.path.abspath(__file__)) + '/c_base/ssa_cpp_solver/makefile'
CBASE_DIR = os.path.join(GILLESPY_PATH, 'c_base/')


class SSACSolver(GillesPySolver):
    name = "SSACSolver"

    def __init__(self, model=None, output_directory=None, delete_directory=True, resume=None, variable=True):
        super(SSACSolver, self).__init__()
        self.__compiled = False
        self.delete_directory = False
        self.model = model
        self.resume = resume
        self.variable = variable

        if self.model is not None:
            # Create constant, ordered lists for reactions/species/
            self.species_mappings = self.model.sanitized_species_names()
            self.species = list(self.species_mappings.keys())
            self.parameter_mappings = self.model.sanitized_parameter_names()
            self.parameters = list(self.parameter_mappings.keys())
            self.reactions = list(self.model.listOfReactions.keys())

            if isinstance(output_directory, str):
                output_directory = os.path.abspath(output_directory)
            
                if isinstance(output_directory, str):
                    if not os.path.isfile(output_directory):
                        self.output_directory = output_directory
                        self.delete_directory = delete_directory
                        if not os.path.isdir(output_directory):
                            os.makedirs(self.output_directory)
                    else:
                        raise gillespyError.DirectoryError("File exists with the same path as directory.")
            else:
                self.temporary_directory = tempfile.TemporaryDirectory()
                self.output_directory = self.temporary_directory.name
                
            if not os.path.isdir(self.output_directory):
                raise gillespyError.DirectoryError("Errors encountered while setting up directory for Solver C++ files.")

            self.__write_template()
            self.__compile()
        
    def __del__(self):
        if self.delete_directory and os.path.isdir(self.output_directory):
            shutil.rmtree(self.output_directory)
        
    def __write_template(self):
        # Open up template file for reading.

        if self.variable:
            template_file = "VariableSimulationTemplate.cpp"
        else:
            template_file = 'SimulationTemplate.cpp'

        with open(os.path.join(GILLESPY_CPP_SSA_DIR, template_file), 'r') as template:
            # Write simulation C++ file.
            template_keyword = "__DEFINE_"
            # Use same lists of model's species and reactions to maintain order
            with open(os.path.join(self.output_directory, 'UserSimulation.cpp'), 'w') as outfile:
                for line in template:
                    if line.startswith(template_keyword):
                        line = line[len(template_keyword):]
                        if line.startswith("VARIABLES"):
                            cutils.write_variables(outfile, self.model, self.reactions, self.species,
                                                    self.parameter_mappings, self.resume, variable=self.variable)
                        if line.startswith("PROPENSITY"):
                            cutils.write_propensity(outfile, self.model, self.species_mappings, self.parameter_mappings
                                                    , self.reactions)
                        if line.startswith("REACTIONS"):
                           cutils.write_reactions(outfile, self.model, self.reactions, self.species)
                        if self.variable:
                            if line.startswith("PARAMETER_UPDATES"):
                                cutils.update_parameters(outfile, self.parameters, self.parameter_mappings)
                    else:
                        outfile.write(line)

    def __compile(self):
        # Use makefile.
        if self.resume:
            if self.resume[0].model != self.model:
                raise gillespyError.ModelError('When resuming, one must not alter the model being resumed.')
        try:
            cmd = ["make", "-C", self.output_directory, '-f', MAKE_FILE, 'UserSimulation',
                   'GILLESPY_CPP_SSA_DIR=' + GILLESPY_CPP_SSA_DIR, 'CBASE_DIR=' + CBASE_DIR]
            built = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except KeyboardInterrupt:
            log.warning(
                "Solver has been interrupted during compile time, unexpected behavior may occur.")

        if built.returncode == 0:
            self.__compiled = True
        else:
            raise gillespyError.BuildError("Error encountered while compiling file:\nReturn code: "
                                           "{0}.\nError:\n{1}\n{2}\n".format(built.returncode,
                                                                             built.stdout.decode('utf-8'),
                                                                             built.stderr.decode('utf-8')))

    def get_solver_settings(self):
        """
        :return: Tuple of strings, denoting all keyword argument for this solvers run() method.
        """
        return ('model', 't', 'number_of_trajectories', 'timeout', 'increment', 'seed', 'debug', 'profile', 'variables')

    def run(self=None, model=None, t=20, number_of_trajectories=1, timeout=0,
            increment=0.05, seed=None, debug=False, profile=False, variables={}, resume=None, **kwargs):

        pause = False

        if resume is not None:
            if t < resume['time'][-1]:
                raise gillespyError.ExecutionError(
                    "'t' must be greater than previous simulations end time, or set in the run() method as the "
                    "simulations next end time")

        if self is None or self.model is None:
            self = SSACSolver(model, resume=resume)

        if len(kwargs) > 0:
            for key in kwargs:
                log.warning('Unsupported keyword argument to {0} solver: {1}'.format(self.name, key))
        
        unsupported_sbml_features = {
                        'Rate Rules': len(model.listOfRateRules),
                        'Assignment Rules': len(model.listOfAssignmentRules), 
                        'Events': len(model.listOfEvents),
                        'Function Definitions': len(model.listOfFunctionDefinitions)
                        }
        detected_features = []
        for feature, count in unsupported_sbml_features.items():
            if count:
                detected_features.append(feature)

        if len(detected_features):
                raise gillespyError.ModelError(
                'Could not run Model.  SBML Feature: {} not supported by SSACSolver.'.format(detected_features))

        if not isinstance(variables, dict):
            raise gillespyError.SimulationError(
                'argument to variables must be a dictionary.')
        for v in variables.keys():
            if v not in self.species+self.parameters:
                raise gillespyError.SimulationError('Argument to variable "{}" \
                is not a valid variable.  Variables must be model species or parameters.'.format(v))

        if self.__compiled:
            self.simulation_data = None
            if resume is not None:
                t = abs(t - int(resume['time'][-1]))

            number_timesteps = int(round(t/increment + 1))

            args = [os.path.join(self.output_directory, 'UserSimulation'),
                    '-trajectories', str(number_of_trajectories),
                    '-timesteps', str(number_timesteps),
                    '-end', str(t)]

            if self.variable:  # Is a variable simulation
                populations = cutils.update_species_init_values(model.listOfSpecies, self.species, variables, resume)
                parameter_values = cutils.change_param_values(model.listOfParameters, self.parameters, model.volume, variables)
                args.extend(['-initial_values', populations, '-parameters', parameter_values])

            if seed is not None:
                if isinstance(seed, int):
                    args.append('-seed')
                    args.append(str(seed))
                else:
                    seed_int = int(seed)
                    if seed_int > 0:
                        args.append('-seed')
                        args.append(str(seed_int))
                    else:
                        raise gillespyError.ModelError("seed must be a positive integer")

            # begin subprocess c simulation with timeout (default timeout=0 will not timeout)
            with subprocess.Popen(args, stdout=subprocess.PIPE, start_new_session=True) as simulation:
                try:
                    if timeout > 0:
                        stdout, stderr = simulation.communicate(timeout=timeout)
                    else:
                        stdout, stderr = simulation.communicate()
                    return_code = simulation.wait()
                except KeyboardInterrupt:
                    os.killpg(simulation.pid, signal.SIGINT)  # send signal to the process group
                    stdout, stderr = simulation.communicate()
                    pause = True
                    return_code = 33
                except subprocess.TimeoutExpired:
                    os.killpg(simulation.pid, signal.SIGINT)  # send signal to the process group
                    stdout, stderr = simulation.communicate()
                    pause = True
                    return_code = 33
            # Decode from byte, split by comma into array
            stdout = stdout.decode('utf-8').split(',')
            # Parse/return results

            if return_code in [0, 33]:
                trajectory_base, timeStopped = cutils.parse_binary_output(number_of_trajectories, number_timesteps,
                                                                          len(model.listOfSpecies), stdout, pause=pause)
                if model.tspan[2] - model.tspan[1] == 1:
                    timeStopped = int(timeStopped)

                # Format results
                self.simulation_data = []
                for trajectory in range(number_of_trajectories):
                    data = {'time': trajectory_base[trajectory, :, 0]}
                    for i in range(len(self.species)):
                        data[self.species[i]] = trajectory_base[trajectory, :, i + 1]

                    self.simulation_data.append(data)
            else:
                raise gillespyError.ExecutionError("Error encountered while running simulation C++ file:"
                                                   "\nReturn code: {0}.\nError:\n{1}\n".
                                                   format(simulation.returncode, simulation.stderr))

            if resume is not None or timeStopped != 0:
                self.simulation_data = cutils.c_solver_resume(timeStopped, self.simulation_data, t, resume=resume)

        return self.simulation_data, return_code

