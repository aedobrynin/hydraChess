;(function() {
  var board = null
  var $board = $('#board')
  var color = null

  var game = null
  var gameFinished = null

  var rating
  var ratingChanges = null

  var $movesList = $('#moves_list')
  var movesArray = null
  var moveIndx = null

  var animation = false

  var $firstMoveAlert = $('#first_move_alert')
  var firstMoveTimer = new Timer('first_move_seconds')

  var $oppDisconnectedAlert = $('#opp_disconnected_alert')
  var oppDisconnectedTimer = new Timer('reconnect_wait_seconds')

  var clockPair = new ClockPair(['clock_a', 'clock_b'], 0)
  clockPair.hide()

  /* -- GAME INFO RELATED FUNCTIONS -- */
  function getFullmoveNumber() {
    var fen = game.fen()
    var fullmoveNumber = parseInt(fen.split(' ')[5])
    return fullmoveNumber
  }

  function getPosByPiece(piece) {
    var board = game.board()
    var bConc = [].concat(...board)
    var indexes = bConc.map((p, indx) => {
      if (p !== null && p.type === piece.type && p.color === piece.color) {
        return indx
      }
    }).filter(val => val !== undefined)

    var positions = indexes.map((cellIndex) => {
      const row = 'abcdefgh'[cellIndex % 8]
      const col = Math.ceil((64 - cellIndex) / 8)
      return row + col
    })

    return positions
  }
  /* -- GAME INFO RELATED FUNCTIONS -- */

  /* -- SOUNDS -- */
  var moveSound = new Howl({
      src: ['/static/sounds/move.mp3']
  })
  var drawOfferSound = new Howl({
      src: ['/static/sounds/draw_offer.mp3']
  })

  var gameStartedSound = new Howl({
      src: ['/static/sounds/game_started.mp3']
  })

  var gameEndedSound = new Howl({
      src: ['/static/sounds/game_ended.mp3']
  })
  /* -- SOUNDS -- */

  function setPlayersInfo(infoA, infoB) {
    $('#info_a').html(`<a href="/user/${infoA.nickname}" class="nickname">${infoA.nickname}</a> (${infoA.rating})`)
    $('#info_b').html(`<a href="/user/${infoB.nickname}" class="nickname">${infoB.nickname}</a> (${infoB.rating})`)
  }

  function setResults(result) {
    var whiteResult = null
    var blackResult = null
    if (result === '1-0') {
      whiteResult = 'won'
      blackResult = 'lost'
    } else if (result === '0-1') {
      whiteResult = 'lost'
      blackResult = 'won'
    } else if (result === '1/2-1/2')  {
      whiteResult = blackResult = 'draw'
    } else if (result === '-') {
      whiteResult = blackResult = 'canceled'
    }

    if (board.orientation() === 'white') {
      $('#info_a').append(` <b>(${blackResult})</b>`)
      $('#info_b').append(` <b>(${whiteResult})</b>`)
    } else {
      $('#info_a').append(` <b>(${whiteResult})</b>`)
      $('#info_b').append(` <b>(${blackResult})</b>`)
    }
  }

  /* -- CHAT RELATED FUNCTIONS -- */

  /*
  function sendMessage() {
    var message = $('#message_input').val().trim()
    $('#message_input').val('')
    if (message === '') return

    sio.emit('send_message', {'message': message})
  }
  */

  /* -- CHAT RELATED FUNCTIONS -- */

  /* -- HIGHLIGHTS RELATED FUNCTIONS -- */
  function removeHighlights() {
    $board.find('.square-55d63')
      .removeClass('highlight-move-from')
      .removeClass('highlight-move-to')
      .removeClass('highlight-check')
  }

  function highlightLastMove() {
    if (game === null || moveIndx < 0) {
      return
    }

    var move = game.undo()
    game.move(move)

    $board.find('.square-' + move.from).addClass('highlight-move-from')
    $board.find('.square-' + move.to).addClass('highlight-move-to')

    if (game.in_check()) {
      var piece = {type: 'k', color: game.turn()}
      var pos = getPosByPiece(piece)[0]
      $board.find('.square-' + pos).addClass('highlight-check')
    }
  }

  /* -- HIGHLIGHTS RELATED FUNCTIONS -- */
  function onDragStart(source, piece, position, orientation) {
    if (gameFinished || color !== piece[0]) return false
    if (moveIndx + 1 !== movesArray.length) {
      moveToEnd()
      return false
    }
  }

  function onDrop(source, target) {
    if (color !== game.turn()) return 'snapback'

    var move = game.move({
      from: source,
      to: target,
      promotion: 'q' // TODO
    })

    // illegal move
    if (move === null) return 'snapback'

    $firstMoveAlert.hide()
    firstMoveTimer.stop()

    if (!game.game_over()) {
      moveSound.play()
    }

    removeHighlights()
    highlightLastMove()

    game.undo()

    sio.emit('make_move', {'san': move.san, 'game_id': gameId})

    declineDrawOfferLocally()
  }

  function onGameStarted(data) {
    if (data.moves !== '') {
      movesArray = data.moves.split(',')
    }    else {
      movesArray = []
    }

    moveIndx = movesArray.length - 1

    game = new Chess()
    movesArray.forEach(function(move, index) {
      pushToMovesList(move, index)
      game.move(move)
    })

    board.position(game.fen())

    highlightLastMove()

    if (data.result === undefined) {
      gameStartedSound.play()
      clockPair.setTimes(data.black_clock, data.white_clock)
      if (game.turn() === 'w' && getFullmoveNumber() !== 1) {
        clockPair.setWorkingClock(1)
      }
      clockPair.show()
      gameFinished = false
    }    else {
      gameFinished = true
    }

    if (data.is_player) {
      color = data.color
      if (color === 'w') {
        rating = data['white_user']['rating']
        board.orientation('white')
      } else {
        if (data.result === undefined) {
          clockPair.rotate()
        }
        rating = data['black_user']['rating']
        board.orientation('black')
      }
      ratingChanges = data.rating_changes

      // Show draw and resign buttons.
      if (data.result === undefined) {
        $('#buttons_container').css('display', 'block')
        $('#draw_btn').prop('accept', false)
        $('#draw_btn').prop('disabled', !data.can_send_draw_offer)
      }
    }

    if (board.orientation() === 'white') {
        setPlayersInfo(data.black_user, data.white_user)
    } else {
        setPlayersInfo(data.white_user, data.black_user)
    }

    if (data.result !== undefined) {
      setResults(data.result)
    }

    // If game is started, start clocks
    if (!(getFullmoveNumber() === 1 && game.turn() === 'w')) {
      clockPair.start()
    }

    updateBoardSize()
 }

 function onGameUpdated(data) {
    clockPair.setTimes(data.black_clock, data.white_clock)

    // There won't be animation, because we already updated board position
    // before. animation = true will block moveToEnd() call.
    if (game.turn() === color) {
      animation = false
    }

    movesArray.push(data.san)
    pushToMovesList(data.san, moveIndx + 1)
    moveToEnd()
    if (!clockPair.works) clockPair.start()
    else clockPair.toggle()

    removeHighlights()
    highlightLastMove()

    // Checking in order to do not do this twice
    if (game.turn() === color && !game.game_over()) {
      moveSound.play()
    }

    $('#draw_btn').prop('disabled', false)
  }

  function onGameEnded(data) {
    /*
    $('#message_input').prop('readonly', true)
    */

    $('#buttons_container').css('display', 'none')

    clockPair.stop()
    setResults(data.result)

    if (color === null) return // Do not do next things, If we are spectators.
    $firstMoveAlert.hide()
    firstMoveTimer.stop()

    $oppDisconnectedAlert.hide()
    oppDisconnectedTimer.stop()

    // Calculate ratingDelta for modal
    var ratingDelta = 0
    if (data.result === '1/2-1/2') {
      ratingDelta = ratingChanges['draw']
    } else if (color === 'w') {
      if (data.result === '1-0') {
        ratingDelta = ratingChanges['win']
      } else if (data.result === '0-1') {
        ratingDelta = ratingChanges['lose']
      }
    } else {
      if (data.result === '1-0')        {
        ratingDelta = ratingChanges['lose']
      } else if (data.result === '0-1') {
        ratingDelta = ratingChanges['win']
      }
    }

    if (ratingDelta > 0) {
      ratingDelta = '+' + ratingDelta
    }
    rating += parseInt(ratingDelta)

    $('#game_results_container')
      .append(`${data.reason}<br />Your new rating: ${rating} (${ratingDelta})`)
    $('#game_results_modal').modal('show')

    gameEndedSound.play()
    gameFinished = true
  }

  function onFirstMoveWaiting(data) {
    var waitTime = data.wait_time

    firstMoveTimer.stop()
    firstMoveTimer.setTime(waitTime)
    firstMoveTimer.start()
    $firstMoveAlert.fadeIn()
  }

  function onOppDisconnected(data) {
    // In order to do not make overlapping alerts.
    if ($firstMoveAlert.css('display') !== 'none') {
      return
    }

    var waitTime = data.wait_time

    oppDisconnectedTimer.stop()
    oppDisconnectedTimer.setTime(waitTime)
    oppDisconnectedTimer.start()
    $oppDisconnectedAlert.fadeIn()
  }

  function onOppReconnected() {
    $oppDisconnectedAlert.hide()
    oppDisconnectedTimer.stop()
  }

  function onDrawOffer() {
    $('#draw_btn').prop('accept', true)
    $('#draw_btn').addClass('bg-warning')
    drawOfferSound.play()
  }

  function acceptDrawOffer() {
    sio.emit('accept_draw_offer')
  }

  function makeDrawOffer() {
    sio.emit('make_draw_offer')
    $('#draw_btn').prop('disabled', true)
  }

  function declineDrawOfferLocally() {
    $('#draw_btn').prop('accept', false)
    $('#draw_btn').removeClass('bg-warning')
  }

  function checkOrientation() {
    var viewportWidth = window.innerWidth
    var viewportHeight = window.innerHeight

    // Ignore quite large devices
    if (Math.min(viewportWidth, viewportHeight) >= 550) {
      return
    }

    if (viewportHeight > viewportWidth) {
      alert('Please, use the landscape mode') // TODO: something beautiful
    }
  }

  function updateBoardSize() {
    var viewportWidth = window.innerWidth
    var viewportHeight = window.innerHeight

    var containerSize
    if (viewportWidth < 992) {
      $('#moves_list').css('display', 'none')
      $('#info_a').css('display', 'none')
      $('#info_b').css('display', 'none')

      if ($('#clock_a').css('display') === 'none') {
        containerSize = Math.floor(
          Math.min(viewportWidth / 10 * 8, viewportHeight / 10 * 8)
        )
      } else {
        containerSize = Math.floor(
          Math.min((viewportWidth - $('#clock_a').width()) / 10 * 8,
                    viewportHeight / 10 * 8)
        )
      }
    } else {
      $('#moves_list').css('display', 'block')
      $('#info_a').css('display', 'block')
      $('#info_b').css('display', 'block')

      containerSize = Math.floor(
        Math.min((viewportWidth - $('#right_container').width()) / 10 * 8,
                  viewportHeight / 10 * 8)
      )
    }

    containerSize -= containerSize % 8 - 1
    $board.width(containerSize)
    $board.height(containerSize)
    board.resize()
    highlightLastMove()

    var boardPos = $board.position()
    $('#buttons_container').css('top', boardPos.top + 30)
    $('#buttons_container').css('left', boardPos.left + $board.width() + 3)
  }

  // should be called before EVERY animation
  function blockAnimation() {
    animation = true
    setTimeout(function() { animation = false }, config.moveSpeed + 30)
  }

  var config = {
    pieceTheme: '../static/img/pieces/{piece}.svg',
    draggable: true,
    onDragStart: onDragStart,
    onDrop: onDrop,
    onChange: blockAnimation,
    highlight: true,
    highlight1: 'highlight-from',
    highlight2: 'highlight-to',
    moveSpeed: 200
  }

  board = Chessboard('board', config)

  $(window).on('load', function() {
    if (localStorage.lastGameTimeValue) {
      $('#search_game_time').val(localStorage.lastGameTimeValue)
    }
  })

  $(window).on('load', checkOrientation)
  $(window).resize(checkOrientation)

  $(window).on('load', updateBoardSize)
  $(window).resize(updateBoardSize)

  var href = window.location.href
  var gameId = href.slice(href.lastIndexOf('/') + 1)

  var sio = io({
    transports: ['websocket'],
    upgrade: false,
    query: {game_id: gameId}
  })

  sio.on('game_started', onGameStarted)
  sio.on('game_updated', onGameUpdated)
  sio.on('game_ended', onGameEnded)
  sio.on('redirect', function(data) {
    window.location.href = data.url
  })
  // sio.on('get_message', onGetMessage)
  sio.on('first_move_waiting', onFirstMoveWaiting)
  sio.on('opp_disconnected', onOppDisconnected)
  sio.on('opp_reconnected', onOppReconnected)
  sio.on('draw_offer', onDrawOffer)
  // sio.on('draw_offer_accepted', onDrawOfferAccepted)
  // sio.on('draw_offer_declined', onDrawOfferDeclined)

  /*
  $('#message_form').on('submit', function(e) {
    e.preventDefault(
    sendMessage()
  })
  */
  $('#draw_btn').on('click', function(e) {
    var $btn = $('#draw_btn')
    if ($btn.prop('accept')) {
      acceptDrawOffer()
    } else {
      makeDrawOffer()
    }
  })

  $('#resign_btn').on('click', function(e) {
    sio.emit('resign')
  })

  function moveBack() {
    if (moveIndx >= 0 && !animation) {
      $movesList.find(`#move_${moveIndx}`).removeClass('halfmove-active')
      moveIndx -= 1
      game.undo()
      board.position(game.fen())
      var $moveCell = $movesList.find(`#move_${moveIndx}`)
      $moveCell.addClass('halfmove-active')
      $movesList.scrollTop(Math.trunc(moveIndx / 2) * $moveCell.height())

      moveSound.play()

      removeHighlights()
      highlightLastMove()
    }
  }

  function moveForward() {
    if (moveIndx + 1 !== movesArray.length && !animation) {
      $movesList.find(`#move_${moveIndx}`).removeClass('halfmove-active')
      moveIndx += 1
      game.move(movesArray[moveIndx])
      board.position(game.fen())
      var $moveCell = $movesList.find(`#move_${moveIndx}`)
      $moveCell.addClass('halfmove-active')
      $movesList.scrollTop(Math.max(
        0,
        Math.trunc(moveIndx / 2) - 2
      ) * $moveCell.height())

      moveSound.play()

      removeHighlights()
      highlightLastMove()
    }
  }

  function moveToBegin() {
    if (moveIndx !== -1 && !animation) {
      $movesList.find(`#move_${moveIndx}`).removeClass('halfmove-active')
      moveIndx = -1
      game.reset()
      board.position(game.fen())
      $movesList.scrollTop(0)

      moveSound.play()

      removeHighlights()
    }
  }

  function moveToEnd() {
    if (moveIndx !== movesArray.length - 1 && !animation) {
      $movesList.find(`#move_${moveIndx}`).removeClass('halfmove-active')
      while (moveIndx + 1 !== movesArray.length) {
        moveIndx += 1
        game.move(movesArray[moveIndx])
      }
      board.position(game.fen())
      $movesList.find(`#move_${moveIndx}`).addClass('halfmove-active')
      $movesList.scrollTop($movesList[0].scrollHeight)

      moveSound.play()

      removeHighlights()
      highlightLastMove()
    }
  }

  $(document).keydown(function(e) {
    if (e.keyCode === 37) moveBack() // left arrow
    else if (e.keyCode === 39) moveForward()  // right arrow
    else if (e.keyCode === 38) moveToBegin()  // up arrow
    else if (e.keyCode === 40) moveToEnd()  // down arrow
  })

  function pushToMovesList(move, indx) {
    $movesList.find('.halfmove').removeClass('halfmove-active')
    if (indx % 2 === 0) {
      $movesList.append(`<div class='row move'>
                          <div id='move_${indx}'
                               class='col halfmove halfmove-active'>
                            ${move}
                          </div>
                          <div class='col'></div>
                         </div>`)
    } else {
      var $moveCell = $movesList.children().last().children().last()
      $moveCell.attr('id', `move_${indx}`)
      $moveCell.addClass('halfmove halfmove-active')
      $moveCell.append(move)
    }
    $movesList.scrollTop($movesList[0].scrollHeight)
  }

  $('body').on('click', '.halfmove', function() {
    $movesList.find(`#move_${moveIndx}`).removeClass('halfmove-active')
    var newMoveIndx = parseInt(this.id.slice(5))
    if (newMoveIndx === moveIndx) {
      return
    }

    while (newMoveIndx < moveIndx) {
      moveIndx -= 1
      game.undo()
    }
    while (newMoveIndx > moveIndx) {
      moveIndx += 1
      game.move(movesArray[moveIndx])
    }
    board.position(game.fen())
    $movesList.find(`#move_${moveIndx}`).addClass('halfmove-active')
    removeHighlights()
    highlightLastMove()
    moveSound.play()
  })

  $('#new_game_btn').on('click', function(e) {
    e.preventDefault()
    sio.emit('search_game', {game_id: gameId})
    $('#stop_search_btn').css('display', 'block')
    $('#new_game_btn').css('display', 'none')
  })

  $('#stop_search_btn').on('click', function(e) {
    e.preventDefault()
    sio.emit('cancel_search')
    $('#new_game_btn').css('display', 'block')
    $('#stop_search_btn').css('display', 'none')
  })

  // Stop search, if modal is closed.
  $('#game_results_modal').on('hide.bs.modal', function() {
    // Means, that we're in search.
    if ($('#stop_game_btn').css('display') !== 'none') {
      sio.emit('cancel_search')
    }
  })
})()
