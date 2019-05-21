def check_velocity_of_path (ps, pid, dt, thr, tstart=0, tend=None):
    if tend is None: tend = ps.pathLength(pid)
    qfinal = ps.configAtParam (pid, tstart)
    from numpy import linspace
    for t in linspace(tstart, tend, num=int((tend-tstart)/dt)):
        if t+dt > tend: continue
        q    = ps.configAtParam (pid, t)
        q_dq = ps.configAtParam (pid, t+dt)
        v    = ps.client.basic.problem.derivativeAtParam (pid, 1, t)

        for i in range(7, len(q)-14):
            qfinal[i] += v[i-1]*dt
            if abs(q[i] + v[i-1]*dt - q_dq[i]) > thr:
                print "At param", t, ", dof", i, ": velocity is wrong", abs(q[i] + v[i-1]*dt - q_dq[i])
    return qfinal
