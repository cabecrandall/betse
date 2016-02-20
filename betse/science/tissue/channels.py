#!/usr/bin/env python3
# Copyright 2014-2016 by Alexis Pietak & Cecil Curry.
# See "LICENSE" for further details.

import numpy as np



def vgSodium(dyna,sim,cells,p):
    '''
    Handle all **targeted voltage-gated sodium channels** (i.e., only
    applicable to specific tissue profiles) specified by the passed
    user-specified parameters on the passed tissue simulation and cellular
    world for the passed time step.

    Channel model uses Hodgkin-Huxley model for voltage gated sodium channels.

    '''

    V = sim.vm[dyna.targets_vgNa]*1000 + 40.0

    alpha_m = (0.1*(25-V))/(np.exp((25-V)/10)-1)
    beta_m = 4.0*np.exp(-V/18)


    alpha_h = 0.07*np.exp(-V/20)
    beta_h = 1/(1 + np.exp((30-V)/10))

    # calculate m channels
    dyna.m_Na = (alpha_m*(1-dyna.m_Na) - beta_m*(dyna.m_Na))*p.dt*1e3 + dyna.m_Na

    dyna.h_Na = (alpha_h*(1-dyna.h_Na) - beta_h*(dyna.h_Na))*p.dt*1e3 + dyna.h_Na

    # as equations are sort of ill-behaved, threshhold to ensure 0 to 1 status
    inds_mNa_over = (dyna.m_Na > 1.0).nonzero()
    dyna.m_Na[inds_mNa_over] = 1.0

    inds_hNa_over = (dyna.h_Na > 1.0).nonzero()
    dyna.h_Na[inds_hNa_over] = 1.0

    inds_mNa_under = (dyna.m_Na < 0.0).nonzero()
    dyna.m_Na[inds_mNa_under] = 0.0

    inds_hNa_under = (dyna.h_Na < 0.0).nonzero()
    dyna.h_Na[inds_hNa_under] = 0.0

    gNa_max = 4.28e-14#(FIXME should be 4.28e-14, testing with lower)

    # Define ultimate activity of the vgNa channel:
    sim.Dm_vg[sim.iNa][dyna.targets_vgNa] = gNa_max*(dyna.m_Na**3)*(dyna.h_Na)

    print(sim.Dm_vg[sim.iNa].max())
    print('-----')


def vgPotassium(dyna,sim,cells,p):
    '''
    Handle all **targeted voltage-gated potassium channels** (i.e., only
    applicable to specific tissue profiles) specified by the passed
    user-specified parameters on the passed tissue simulation and cellular
    world for the passed time step.
    '''
     # detecting channels to turn on:
    V = sim.vm[dyna.targets_vgK]*1000 + 20.0

    alpha_n = (0.01*(10 - V))/(np.exp((10-V)/10)-1)
    beta_n = 0.125*np.exp(-V/80)

    dyna.n_K = (alpha_n*(1-dyna.n_K) - beta_n*dyna.n_K)*p.dt*1e3 + dyna.n_K

    gK_max = 1.28e-14

    inds_nK_over = (dyna.n_K > 1.0).nonzero()
    dyna.n_K[inds_nK_over] = 1.0

    inds_nK_under = (dyna.n_K < 0.0).nonzero()
    dyna.n_K[inds_nK_under] = 0.0

    sim.Dm_vg[sim.iK][dyna.targets_vgK] = (dyna.n_K**4)*gK_max
    print(sim.Dm_vg[sim.iK].max())
    print('****')



# Wastelands
#------------------------

#def sigmoid(V,po,p1,p2,p3):
#     """
#      Template for typical channel voltage-dependent parameter function m_inf or tau_inf,
#      used in Hodgkin-Huxley channel models.
#
#      Parameters:
#      ------------
#      Input parameters describe the equation:
#
#      po + p1/(1 + exp((V - p2)/p3)
#
#      Returns
#      --------
#      f          The value of the sigmoid function
#     """
#
#     f = po + (p1/(1 + np.exp((V-p2)/p3)))
#
#     return f
#
# def alpha(V,po,p1,p2,p3):
#
#     f = (po*(p1-V))/(np.exp((p2-V)/p3)-1)
#
#     return f
#
# def beta(V, po, p1):
#
#     f = po*np.exp(-V/p1)





