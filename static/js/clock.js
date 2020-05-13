function addLeadingZero(value) {
  if (value < 10) return '0' + value
  return value.toString()
}

class Clock {
  constructor(domId, seconds = 0) {
    this.domId = domId
    this.work = false
    this.setTime(seconds)
  }

  setDomId(domId) {
    this.domId = domId
    this.redraw()
  }

  setTime(seconds) {
    if (Number.isNaN(seconds)) {
      alert(`Expected number for Clock.seconds got '${seconds}'`)
      return
    }
    this.seconds = Math.trunc(seconds)
    this.redraw()
  }

  stop() {
    this.work = false
  }

  start() {
    this.work = true
    this.update()
  }

  toggle() {
    if (this.work) this.stop()
    else this.start()
  }

  redraw() {
    var minutes = addLeadingZero(Math.floor(this.seconds / 60))
    var seconds = addLeadingZero(this.seconds % 60)
    document.getElementById(this.domId).innerHTML = minutes + ':' + seconds
  }

  update() {
    if (this.work === false || this.seconds === 0) {
      return
    }

    this.seconds -= 1
    this.redraw()
    if (this.seconds !== 0) {
      setTimeout(function() { this.update() }.bind(this), 1000)
    }
}
  }

  hide() {
    $(`#${this.domId}`).css('display', 'none')
  }

  show() {
    $(`#${this.domId}`).css('display', 'block')
  }
}

class Timer extends Clock {
  redraw() {
    document.getElementById(this.domId).innerHTML = this.seconds
  }
}

class ClockPair {
  constructor(domIds, seconds = 0) {
    if (!Array.isArray(domIds) || domIds.length !== 2) {
      alert('Bad domIds for ClockPair instance')
      return
    }
    this.clocks = [new Clock(domIds[0], seconds), new Clock(domIds[1], seconds)]
    this.rotated = false
    this.workingClock = 0
    this.works = false
  }

  setTime(clockIndx, seconds) {
    if (!Number.isInteger(clockIndx) || !(clockIndx >= 0 && clockIndx <= 1)) {
      alert(`Bad clock index '${clockIndx}' for setTime in ClockPair instance`)
    }
    this.clocks[clockIndx].setTime(seconds)
  }

  setTimes(timeA, timeB) {
    this.clocks[0].setTime(timeA)
    this.clocks[1].setTime(timeB)
  }

  setWorkingClock(workingClock) {
    var isWorking = this.clocks[this.workingClock].work
    this.clocks[this.workingClock].stop()
    this.workingClock = workingClock
    if (isWorking) {
      this.clocks[this.workingClock].start()
    }
  }

  rotate() {
    this.rotated = !this.rotated
    var domIdA = this.clocks[0].domId
    var domIdB = this.clocks[1].domId
    this.clocks[0].setDomId(domIdB)
    this.clocks[1].setDomId(domIdA)
  }

  setRotation(rotation) {
    if (rotation === this.rotated) {
      return
    }
    this.rotate()
  }

  toggle() {
    for (let i = 0; i < 2; ++i) {
      this.clocks[i].toggle()
    }
    this.workingClock = 1 - this.workingClock
  }

  stop() {
    this.clocks[this.workingClock].stop()
    this.works = false
  }

  start() {
    this.clocks[this.workingClock].start()
    this.works = true
  }

  reset() {
    this.setRotation(false)
  }

  hide() {
    for (let clock of this.clocks) {
      clock.hide()
    }
  }

  show() {
    for (let clock of this.clocks) {
      clock.show()
    }
  }
}
