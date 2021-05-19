#pragma once

/* User-defined parameters go into a file of this same name.
 * Any definitions provided in this template will override the default parameters.
 *
 * Below is a list of configurable model parameters.
 * 
 ******************************************************
 *** GPY_PROPENSITIES: stochastic propensity values ***
 * 
 *   Example:
 *     #define GPY_PROPENSITIES \
 *     PROPENSITY(id, prop) \
 *     (xN)
 *   
 *   Any number of PROPENSITY(id, prop) definitions may be defined.
 *   "id" is an integer value for the propensity ID.
 *   "prop" is the actual propensity formula.
 *   Use S[i] to reference the state of species i.
 * 
 *************************************************************
 *** GPY_ODE_PROPENSITIES: deterministic propensity values ***
 *
 *   Example: 
 *     #define GPY_ODE_PROPENSITIES \
 *     PROPENSITY(id, prop) \
 *     (xN)
 * 
 *   Same as GPY_PROPENSITIES.
 *   Only difference is that the values of S[i] are doubles rather than ints.
 *   Not required if GPY_PROPENSITIES is already defined, or using a non-ODE simulation.
 * 
 ***********************************************************************
 *** GPY_INIT_POPULATIONS: initial population value for each species ***
 *** GPY_NUM_SPECIES: total number of species in simulation model    ***
 *   
 *   Example:
 *     #define GPY_NUM_SPECIES 3
 *     #define GPY_INIT_POPULATIONS {0, 100, 25}
 * 
 *   Both are required for all models.
 *   GPY_NUM_SERIES is an integer value.
 *   GPY_INIT_POPULATIONS is a 1D array initializer.
 *   The size of GPY_INIT_POPULATIONS must equal GPY_NUM_SPECIES.
 * 
 **********************************************************************
 *** GPY_REACTIONS: stoichiometry matrix for a list of reactions.   ***
 *** GPY_NUM_REACTIONS: number of reactions in stoichometry matrix. ***
 * 
 *   Example:
 *     #define GPY_NUM_REACTIONS 3
 *     #define GPY_REACTIONS { {0, 1, -1}, {1, -1, 1}, {0, 0, 1} }
 * 
 *   First dimension is reaction R_i.
 *   Second dimension is the species change list for reaction R_i.
 *   In the above example, R_0 has species change list of {0, 1, -1},
 *     which equates to S_3 being a reactant and S_2 being a product:
 *     S_3 -> S_2
 *   The number of reactions in the first dimension of GPY_REACTION must match GPY_NUM_REACTIONS.
 *   The number of species changes in each reaction's change list must match GPY_NUM_SPECIES.
 * 
 ****************************************************************************
 *** GPY_SPECIES_NAMES: list of strings representing names of species.    ***
 *** GPY_REACTION_NAMES: list of strings representing names of reactions. ***
 * 
 *   Example:
 *     #define GPY_SPECIES_NAMES { "S_1", "S_2", "S_3" }
 *     #define GPY_REACTION_NAMES { "R_1", "R_2", "R_3" }
 * 
 *   Both definitions are 1D array initializers and are required for all models.
 *   In this list, the reaction/species at index i will map to their respective
 *     reaction/species defined in GPY_REACTIONS and GPY_INIT_POPULATIONS.
 * 
 ************************************************************
 *** GPY_VOLUME: double representing the solution volume. ***
 * 
 *   Example:
 *     #define GPY_VOLUME 5.1
 * 
 *   Sets the volume of the solution.
 *   Intended to be used by certain mass-action rates or propensities.
 *   Only required for models where volume V is required for the model.
 */
