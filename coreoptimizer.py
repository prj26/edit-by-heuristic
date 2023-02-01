import cv2
import numpy as np

import videoedit


def videoFrameGenerator(filename):
    # partially adapted from a stackoverflow answer
    # https://stackoverflow.com/questions/42163058/how-to-turn-a-video-into-numpy-array

    cap = cv2.VideoCapture(filename)
    frameCount = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    fc = 0
    ret = True

    while (fc < frameCount and ret):
        ret, a = cap.read()
        yield a
        fc += 1

    cap.release()


class FrameTimeline():
    def __init__(self, filename, startTime):
        self.filename = filename
        self.startTime = startTime

        cap = cv2.VideoCapture(filename)
        frameCount = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        self.fps = cap.get(cv2.CAP_PROP_FPS)

        cap.release()

    def getIterator(self):
        return FrameTimelineIterator(self)

    def getNFrameIterator(self, multiple):
        iterator = FrameTimelineIterator(self)
        return NFrameTimelineIterator(iterator, multiple)


class FrameTimelineIterator():
    def __init__(self, frameTimeline):
        self.filename = frameTimeline.filename
        self.cap = cv2.VideoCapture(frameTimeline.filename)
        self.hasNextFrame, self.currentFrame = self.cap.read()
        if self.hasNextFrame:
            self.hasNextFrame, self.nextFrame = self.cap.read()
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.currentTime = frameTimeline.startTime
        self.timeDelta = 1 / self.fps
        self.frameDuration = self.timeDelta

    def getTotalFrameCount(self):
        return self.cap.get(cv2.CAP_PROP_FRAME_COUNT)

    def peekNextFrame(self):
        return self.nextFrame

    def peekNextTime(self):
        return self.currentTime + self.timeDelta

    def iterate(self):
        self.currentFrame = self.nextFrame
        self.currentTime += self.timeDelta
        if self.hasNextFrame:
            self.hasNextFrame, self.nextFrame = self.cap.read()
        else:
            del self.nextFrame

class NFrameTimelineIterator():
    def __init__(self, frameTimelineIterator, multiple):
        self.frameTimelineIterator = frameTimelineIterator
        self.multiple = multiple
        self.filename = frameTimelineIterator.filename

        self.fps = frameTimelineIterator.fps / multiple
        self.currentTime = frameTimelineIterator.currentTime
        self.timeDelta = 1 / self.fps

        self.hasImmediateNext, self.currentFrame = frameTimelineIterator.hasNextFrame, frameTimelineIterator.currentFrame
        i = 0
        while i < multiple and self.hasImmediateNext:
            frameTimelineIterator.iterate()
            self.hasImmediateNext = frameTimelineIterator.hasNextFrame
            i += 1

        self.frameDuration = i * frameTimelineIterator.frameDuration
        if i == multiple:
            self.nextFrame = frameTimelineIterator.currentFrame
            self.hasNextFrame = True
        else:
            self.hasNextFrame = False

    def getTotalFrameCount(self):
        return self.frameTimelineIterator.getTotalFrameCount() // self.multiple

    def peekNextFrame(self):
        return self.nextFrame

    def iterate(self):
        self.currentFrame = self.nextFrame
        if self.currentFrame is None:
            print("current frame is none after iteration")
        self.currentTime += self.timeDelta
        i = 0
        while i < self.multiple and self.hasImmediateNext:
            self.frameTimelineIterator.iterate()
            self.hasImmediateNext = self.frameTimelineIterator.hasNextFrame
            i += 1
        self.frameDuration = i * self.frameTimelineIterator.frameDuration
        if i == self.multiple:
            self.nextFrame = self.frameTimelineIterator.currentFrame
            self.hasNextFrame = True
        else:
            self.hasNextFrame = False
            del self.nextFrame
            print("deleted nextFrame, so it might be null now")

class Cut():
    def __init__(self, timeBefore, filenameBefore, timeAfter, filenameAfter):
        self.timeBefore = timeBefore
        self.timeAfter = timeAfter
        self.filenameBefore = filenameBefore
        self.filenameAfter = filenameAfter

    def __repr__(self):
        return "<Cut from " + self.filenameBefore + "(" + str(self.timeBefore) + ") at " + videoedit.formatTime(self.timeBefore) + "to " + self.filenameAfter + "(" + str(self.timeAfter) + ") at " + videoedit.formatTime(self.timeAfter) + " >"


class OptimizationState():
    uniqueStateIndex = 0

    def __init__(self, currentIterator, filename, currentTotalScore, currentTime, expiryTime, cutHistory,
                 timeSinceLastCut, heuristicScorePerSecond, hasValidHistory=True):
        self.uniqueStateIndex = OptimizationState.uniqueStateIndex
        OptimizationState.uniqueStateIndex += 1
        self.currentIterator = currentIterator
        self.filename = filename
        self.currentTotalScore = currentTotalScore
        self.currentTime = currentTime
        self.startTime = currentTime
        self.expiryTime = expiryTime
        self.cutHistory = cutHistory
        self.timeSinceLastCut = timeSinceLastCut
        self.heuristicScorePerSecond = heuristicScorePerSecond
        self.hasValidHistory = hasValidHistory

    def incrementTime(self, timeDelta):
        self.currentTotalScore += (self.heuristicScorePerSecond * timeDelta)
        self.currentTime += timeDelta
        self.timeSinceLastCut += timeDelta

    def __repr__(self):
        return "<state id:" + str(self.uniqueStateIndex) + " f:" + self.filename + ", current:" + str(
            self.currentTime) + " ("+videoedit.formatTime(self.currentTime)+"), expiry:" + str(
            self.expiryTime) + ">"


class FrameTimelinesOptimizer():
    def __init__(self, filenames, startTimes):
        self.filenames = filenames
        self.frameTimelines = [FrameTimeline(filename, startTimes[filename]) for filename in filenames]
        self.start_times = startTimes

    def optimizeWithFixedCosts(self, frameHeuristic, cutCost, resolutionRreciprocal=1):
        # make iterators
        if resolutionRreciprocal == 1:
            iterators = [i.getIterator() for i in self.frameTimelines]
        else:
            iterators = [i.getNFrameIterator(resolutionRreciprocal) for i in self.frameTimelines]
        currentTime = min(i.currentTime for i in iterators)

        # make states
        states = []
        for iterator in iterators:
            states.append(OptimizationState(iterator, iterator.filename, 0, iterator.currentTime,
                                            iterator.currentTime + iterator.timeDelta, [], 0,
                                            frameHeuristic(iterator.currentFrame, 1), iterator.currentTime == 0))

        totalFramesProcessed = 0
        totalFramesToProcess = sum(iterator.getTotalFrameCount() for iterator in iterators)
        print([iterator.getTotalFrameCount() for iterator in iterators])
        nextFramePrint = 1
        # repeat while there are still iterators running
        debugPrints = True

        def dprint(*args, **kwargs):
            if debugPrints:
                print(*args, **kwargs)

        while max(i.hasNextFrame for i in iterators):
            # get next point in time to jump to
            nextExpiry = min(i.expiryTime for i in states)
            dprint("considering next expiry:")
            for state in states:
                dprint("  state",state,"has hasNextFrame value",state.currentIterator.hasNextFrame)
            dprint("nextExpiry:", nextExpiry)
            if len([i.currentTime for i in states if i.currentTime > currentTime]) > 0:
                nextCurrent = min(i.currentTime for i in states if i.currentTime > currentTime)
            else:
                nextCurrent = float('inf')
            dprint("nextCurrent:", nextCurrent)
            if nextCurrent < nextExpiry:
                nextTime = nextCurrent
                frameWillExpire = False
                print("bringing nextCurrent in: currentTime is",videoedit.formatTime(currentTime))
                print("and NEXTTIME is",videoedit.formatTime(nextTime))
            else:
                nextTime = nextExpiry
                frameWillExpire = True
            delta = nextTime - currentTime
            # increment states
            for state in states:
                if state.currentTime < nextTime:
                    dprint("  Commencing incrementTime for state with filename",state.filename)
                    dprint("  before, state time is ",state.currentTime)
                    state.incrementTime(delta)
                    state.currentTime = nextTime
                    dprint("  after, state time is",state.currentTime)
                    # ^ technically unecessary but I'm paranoid about floating point errors
            if frameWillExpire:
                dprint("at least one frame expires this iteration")
                expiredStates = [state for state in states if state.expiryTime == nextTime]
                dprint("expiredStates: ", expiredStates)
                newStates = []
                toRemove = []
                for expiredState in expiredStates:
                    expiredState.hasIterated = False
                #check for states with no successort and add them to toRemove
                for expiredState in expiredStates:
                    if not expiredState.hasIterated:
                        if expiredState.currentIterator.hasNextFrame:
                            if expiredState.currentIterator.nextFrame is None:
                                print("(in optimizer) object claims to have next frame but nextframe is actually none")
                            dprint("iterating expired state's iterator", expiredState)

                            expiredState.currentIterator.iterate()

                            expiredState.hasIterated = True
                            expiredState.heuristicScorePerSecond = frameHeuristic(
                                expiredState.currentIterator.currentFrame, 1)
                        else:
                            dprint(expiredState, "has no next frame, cannot iterate")
                            toRemove.append(expiredState)

                for toRemoveState in toRemove:
                    dprint("removing expired state with no next frame from expiredStates")
                    dprint("(no point looking for histories for a state that doesn't exist)")
                    expiredStates.remove(toRemoveState)
                    print("removing expired state",toRemoveState.filename,"at",videoedit.formatTime(currentTime))
                    states.remove(toRemoveState)

                possibleNextStates = []
                for expiredState in expiredStates:
                    dprint("creating possible history for ", expiredState, "'s sequel")
                    # produce a list of possible histories for the next frame
                    for state in states:
                        if state.currentTime == nextTime and state.hasValidHistory:
                            possibleState = OptimizationState(expiredState.currentIterator, expiredState.filename,
                                                              state.currentTotalScore if expiredState.filename == state.filename else state.currentTotalScore - cutCost, nextTime,
                                                              nextTime + expiredState.currentIterator.frameDuration,
                                                              expiredState.cutHistory if expiredState.filename == state.filename else state.cutHistory + [
                                                                  Cut(state.startTime, state.filename, nextTime,
                                                                      expiredState.filename)],
                                                              expiredState.timeSinceLastCut if (
                                                                      expiredState.filename == state.filename) else 0,
                                                              expiredState.heuristicScorePerSecond)
                            dprint("created possible new state", possibleState, "with history of", state)
                            possibleNextStates.append(possibleState)
                        else:
                            dprint("ignoring desynchronised/invalidhistory state", state)
                dprint("about to perform reduction of possibleNextStates, containing", len(possibleNextStates), "items")
                self.reduceFramesOnly(possibleNextStates)
                dprint("after reduction, possibleNextStates is ", possibleNextStates)
                for expiredState in expiredStates:
                    dprint("removing from states expired state", expiredState)
                    states.remove(expiredState)
                dprint("extending states by possibleNextStates")
                states.extend(possibleNextStates)
            else:
                dprint("no frames expired")
            currentTime = nextTime
            totalFramesProcessed += 1
            if currentTime > 315:
                debugPrints = True
            else:
                debugPrints = False
            if totalFramesProcessed == nextFramePrint or debugPrints:
                nextFramePrint *= 2
                print("processed", totalFramesProcessed, "frames out of", totalFramesToProcess)
                print((totalFramesProcessed / totalFramesToProcess) * 100, "% complete")
                print("number of optimization states:", len(states))
                print("currentTime:", currentTime,"("+videoedit.formatTime(currentTime)+")")

        bestFinalState = states[0]
        print("getting a final state")
        for state in states:
            if state.currentTotalScore > bestFinalState.currentTotalScore:
                bestFinalState = state
        print("printing state info to resolve discrepancy")
        print("bestFinalState.filename is ",bestFinalState.filename)
        print("start_times[bestFinalState.filename] is ",self.start_times[bestFinalState.filename])
        from moviepy.editor import VideoFileClip
        print("duration of the VideoFileClip corresponding to this filename is ",VideoFileClip(bestFinalState.filename).duration)
        print("state iterator fps is ",bestFinalState.currentIterator.fps)
        print("state iterator frame count is",bestFinalState.currentIterator.getTotalFrameCount())
        print("duration extrapolated from frame count and fps is ",bestFinalState.currentIterator.getTotalFrameCount()/bestFinalState.currentIterator.fps)

        return bestFinalState

    def reduceFramesOnly(self, statesToReduce):
        bestForEachFilename = {}
        for state in statesToReduce:
            if state.filename not in bestForEachFilename:
                bestForEachFilename[state.filename] = state
            else:
                if state.currentTotalScore > bestForEachFilename[state.filename].currentTotalScore:
                    bestForEachFilename[state.filename] = state
        log = []
        log.append("at the beginning, statesToReduce is " + str(statesToReduce))
        log.append("about to remove states for in dictionary")
        toRemove = []
        for state in statesToReduce:
            log.append("looking at state " + str(state))
            if state not in bestForEachFilename.values():
                log.append("state " + str(state) + " not in dictionary values, removing (i.e. adding to toRemove)")
                currentCount = len(statesToReduce)
                toRemove.append(state)
            else:
                log.append(str(state) + " is in " + str(list(bestForEachFilename.values())))
        for toRemoveState in toRemove:
            statesToReduce.remove(toRemoveState)
        if len(statesToReduce) > 1:
            print("bestForEachFilename:", bestForEachFilename)
            print("bestForEachFilename values are ", list(bestForEachFilename.values()))
            print("statesToReduce:", statesToReduce)
        if len(set([i.filename for i in statesToReduce])) != len(statesToReduce):
            print("\n".join(log))
            raise ValueError("identical files left over, throwing exception")

def product(array):
    p = 1
    for item in array:
        p *= item
    return p

def brightheuristic(frame, duration):
    if frame is None:
        print("brightHeuristic recieved None as input")
    return duration * frame.sum() / (product(np.shape(frame)) * 255)


def darkheuristic(frame, duration):
    return -brightheuristic(frame, duration)
