#/usr/bin/env python
from hpp.corbaserver.manipulation.robot import Robot
from hpp.corbaserver.manipulation import newProblem, ProblemSolver, ConstraintGraph, Rule
from hpp.gepetto.manipulation import ViewerFactory
from hpp import Transform
import CORBA, sys, numpy as np
from math import sqrt

newProblem()

Robot.packageName = "talos_data"
Robot.urdfName = "talos"
Robot.urdfSuffix = '_full'
Robot.srdfSuffix= ''

class Mire (object):
  rootJointType = 'freeflyer'
  packageName = 'sot_hpp_demo'
  urdfName = 'calibration_mire'
  urdfSuffix = ""
  srdfSuffix = ""
  name = "mire"
  handles = [ "mire/left", "mire/right" ]

half_sitting = [
        0,0,1.0192720229567027,0,0,0,1, # root_joint
        0.0, 0.0, -0.411354, 0.859395, -0.448041, -0.001708, # leg_left
        0.0, 0.0, -0.411354, 0.859395, -0.448041, -0.001708, # leg_right
        0, 0.006761, # torso
        0.25847, 0.173046, -0.0002, -0.525366, 0, 0, 0.1, # arm_left
        0, 0, 0, 0, 0, 0, 0, # gripper_left
        -0.25847, -0.173046, 0.0002, -0.525366, 0, 0, 0.1, # arm_right
        0, 0, 0, 0, 0, 0, 0, # gripper_right
        0, 0, # head

        0.5,0,1.1,-0.5,-0.5, 0.5, 0.5, # mire
        ]

def makeProblem ():
    robot = Robot ('dev', 'talos', rootJointType = "freeflyer")
    robot. leftAnkle = "talos/leg_left_6_joint"
    robot.rightAnkle = "talos/leg_right_6_joint"

    robot.setJointBounds ("talos/root_joint", [-1, 1, -1, 1, 0.5, 1.5])

    ps = ProblemSolver (robot)
    ps.selectPathProjector("Progressive", 0.2)
    ps.setErrorThreshold (1e-3)
    ps.setMaxIterProjection (40)
    ps.addPathOptimizer("SimpleTimeParameterization")

    vf = ViewerFactory (ps)
    vf.loadObjectModel (Mire, 'mire')
    robot.setJointBounds ("mire/root_joint", [-0, 1, -1, 1, 0, 2])

    return robot, ps, vf

def makeGraph(robot, objectCanFly=False):
    rules = [   Rule([ "talos/left_gripper", ], [ Mire.handles[0], ], True),
                Rule([ "talos/right_gripper", ], [ Mire.handles[1], ], True),]
    if objectCanFly:
        rules.append ( Rule([ "talos/right_gripper", "talos/left_gripper", ], [ "","", ], True) )

    graph = ConstraintGraph.buildGenericGraph(robot, 'graph',
            [ "talos/left_gripper", "talos/right_gripper", ],
            [ "mire", ],
            [ Mire.handles, ],
            [ [ ], ],
            [ ],
            rules)
    return graph

robot, ps, vf = makeProblem()
# ps.setRandomSeed(123)
robot.setCurrentConfig(half_sitting)

q_init = robot.getCurrentConfig()

ps.addPartialCom ("talos", ["talos/root_joint"])
ps.addPartialCom ("talos_mire", ["talos/root_joint", "mire/root_joint"])

ps.createStaticStabilityConstraints ("balance", half_sitting, "talos", ProblemSolver.FIXED_ON_THE_GROUND)
foot_placement = [ "balance/pose-left-foot", "balance/pose-right-foot" ]
foot_placement_complement = [ ]

robot.setCurrentConfig(half_sitting)
com_wf = np.array(ps.getPartialCom("talos"))
tf_la = Transform (robot.getJointPosition(robot.leftAnkle))
com_la = tf_la.inverse().transform(com_wf)

ps.createRelativeComConstraint ("com_talos_mire", "talos_mire", robot.leftAnkle, com_la.tolist(), (True, True, True))
ps.createRelativeComConstraint ("com_talos"     , "talos"     , robot.leftAnkle, com_la.tolist(), (True, True, True))

ps.createPositionConstraint ("gaze", "talos/rgbd_optical_joint", "mire/root_joint", (0,0,0), (0,0,0), (True, True, False))

left_gripper_lock = []
right_gripper_lock = []
other_lock = ["talos/torso_1_joint"]
for n in robot.jointNames:
    s = robot.getJointConfigSize(n)
    r = robot.rankInConfiguration[n]
    if n.startswith ("talos/gripper_right"):
        ps.createLockedJoint(n, n, half_sitting[r:r+s])
        right_gripper_lock.append(n)
    elif n.startswith ("talos/gripper_left"):
        ps.createLockedJoint(n, n, half_sitting[r:r+s])
        left_gripper_lock.append(n)
    elif n in other_lock:
        ps.createLockedJoint(n, n, half_sitting[r:r+s])

graph = makeGraph (robot, objectCanFly=True)
graph.setConstraints (graph=True,
        lockDof = left_gripper_lock + right_gripper_lock + other_lock,
        numConstraints = [ "com_talos_mire", "gaze"] + foot_placement)
graph.initialize()

# res, q_init, err = graph.applyNodeConstraints("talos/left_gripper grasps mire/left", half_sitting)
# res, q_goal, err = graph.applyNodeConstraints("talos/right_gripper grasps mire/right", half_sitting)
# print ps.directPath(q_init, q_init, True)
# ps.setInitialConfig(q_init)
# ps.addGoalConfig(q_goal)
ps.setParameter("SimpleTimeParameterization/safety", 0.5)
ps.setParameter("SimpleTimeParameterization/order", 2)

# ps.solve()

ps.client.manipulation.problem.selectProblem("estimation")
robotEst, psEst, vfEst = makeProblem()
graphEst = makeGraph(robotEst, objectCanFly=True)
graphEst.initialize()

psEst.setParameter("SimpleTimeParameterization/safety", 0.5)
psEst.setParameter("SimpleTimeParameterization/order", 2)
psEst.setMaxIterPathPlanning(50)

ps.client.manipulation.problem.selectProblem("default")

# Generation of poses

def setGaussianShooter (q, left = True, high = 1, low=0.01):
    ps.setParameter("ConfigurationShooter/Gaussian/useRobotVelocity", True)
    v = [0,] * robot.getNumberDof()
    for n in robot.jointNames:
        s = robot.rankInVelocity[n]
        e = s+robot.getJointNumberDof(n)
        if (left and n.startswith("talos/arm_left")) or (not left and n.startswith("talos/arm_right")):
            v[s:e] = [high,] * (e-s)
        else:
            v[s:e] = [low,] * (e-s)
    robot.setCurrentConfig(q)
    robot.client.basic.robot.setCurrentVelocity(v)
    robot.client.basic.problem.selectConfigurationShooter("Gaussian")
    ps.setParameter("ConfigurationShooter/Gaussian/useRobotVelocity", False)

def generateValidConfig (left = True):
    setGaussianShooter(half_sitting, left)
    if left: nodename = "talos/left_gripper grasps mire/left"
    else:    nodename = "talos/right_gripper grasps mire/right"

    while True:
        qrand = robot.shootRandomConfig ()
        res, qproj, err = graph.applyNodeConstraints(nodename, qrand)
        if res:
            res, msg = robot.isConfigValid (qproj)
            if res: return qproj

def interactiveGenerate (nb = 10, left = True):
    v = vf.createViewer()
    qs = []
    while True:
        q = generateValidConfig(left)
        v (q)
        ok = True
        while ok:
            answer = raw_input ("Keep configuration ? [y/n]")
            if answer == "y":
                qs.append(q)
                ok = False
                if len(qs) == nb: return
            elif answer == "n":
                ok = False
