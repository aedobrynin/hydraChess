;(function() {
  var board = null
  var $board = $('#board')
  var color = null
  var game = null
  var game_finished = null
  var $movesList = $('#moves_list')
  var movesArray = null
  var moveIndx = null
  var clockPair = new ClockPair(['clock_a', 'clock_b'], 0)
  clockPair.hide()

  /* -- GAME INFO RELATED FUNCTIONS -- */
  function getFullmoveNumber() {
    if (game == null) return 0
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

  /* -- SOUNDS RELATED FUNCTIONS -- */
  function playGameStartedSound() {
    $('#game_started_sound').trigger('play')
  }

  function playMoveSound() {
    $('#move_sound').trigger('play')
  }

  function playGameEndedSound() {
    $('#game_ended_sound').trigger('play')
  }

  function playDrawOfferSound() {
    $('#draw_offer_sound').trigger('play')
  }
  /* -- SOUNDS RELATED FUNCTIONS -- */

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
    move = game.undo()
    game.move(move)

    console.log(move)
    $board.find('.square-' + move.from).addClass('highlight-move-from')
    $board.find('.square-' + move.to).addClass('highlight-move-to')

    if (game.in_check()) {
      var piece = {type: 'k', color: game.turn()}
      var pos = getPosByPiece(piece)[0]
      $board.fin('.square-' + pos).addClass('highlight-check')
    }
  }

  /* -- HIGHLIGHTS RELATED FUNCTIONS -- */

  function onDragStart(source, piece, position, orientation) {
    if (game_finished || color !== piece[0]) return false
    if (moveIndx + 1 !== movesArray.length) {
      moveToEnd()
      return false
    }
  }

  function onDrop(source, target) {
    if (game == null) return 'snapback'
    if (color !== game.turn()) return 'snapback'

    var move = game.move({
      from: source,
      to: target,
      promotion: 'q' // TODO
    })

    // illegal move
    if (move === null) return 'snapback'

    //removeHighlights()
    //removeTimer('first_move_timer')

    if (game.in_check()) {
      highlightChecked()
    }

    if (!game.game_over()) {
      playMoveSound()
    }

    addHighlights(source, target)

    game.undo()

    sio.emit('make_move', {'san': move.san, 'game_id': game_id})
    declineDrawOfferLocally()
  }

  function onGameStarted(data) {
    console.log(data)

    if (data.moves !== "") {
      movesArray = data.moves.split(',')
    }
    else {
      movesArray = []
    }

    moveIndx = movesArray.length - 1

    game = new Chess()
    movesArray.forEach(function (move, index) {
      pushToMovesList(move, index)
      game.move(move)
    })

    board.position(game.fen())
    highlightLastMove()

    /*
    playGameStartedSound()
    */

    if (data.result === undefined) {
      clockPair.setTimes(data.black_clock, data.white_clock)
      if (game.turn() === 'w' && getFullmoveNumber() !== 1)
        clockPair.setWorkingClock(1)
      clockPair.show()
      game_finished = false
    }
    else
      game_finished = true


    if (data.is_player) {
      color = data.color
      if (color === 'w') {
        board.orientation('white')
      } else {
        if (data.result === undefined)
          clockPair.rotate()
        board.orientation('black')
      }
    }

    /*
    if (data.last_move) {
      addHighlights(data.last_move.slice(0, 2),
                    data.last_move.slice(2, 4))
    }

    if (game.in_check()) {
      highlightChecked()
    }
    */

    // If game is started, start clocks
    if (!(getFullmoveNumber() === 1 && game.turn() === 'w')) {
      clockPair.start()
    }
    /*
    ratingChanges = data.rating_changes
    var oppNickname = data.opp_nickname
    var oppRating = data.opp_rating
    $('#opp_nickname').html(oppNickname)
    $('#opp_rating').html(`(${oppRating})`)

    $('#message_input').prop('readonly', false)

    $('#search_game_form').addClass('d-none')
    $('#game_state_buttons').removeClass('d-none')

    $('#draw_btn').html('Offer a draw')
    $('#draw_btn').prop('accept', false)
    $('#draw_btn').prop('disabled', !data.can_send_draw_offer)
    */
  }

  function onGameUpdated(data) {
    console.log(data)

    clockPair.setTimes(data.black_clock, data.white_clock)

    movesArray.push(data.san)
    pushToMovesList(data.san, moveIndx + 1)
    moveToEnd()

    if (getFullmoveNumber() === 1) clockPair.start()
    else clockPair.toggle()

    if (game.in_check()) {
      highlightChecked()
    }

    if (game.turn() === color && !game.game_over()) {
      // Checking in order to do not do this twice
      playMoveSound()
    }

    $('#draw_btn').prop('disabled', false)
 }

  function onGameEnded(data) {
    $('#message_input').prop('readonly', true)
    $('#search_game_form').prop('inSearch', false)
    $('#search_game_time').removeClass('d-none')
    $('#search_spinner').removeClass('d-flex')
      .addClass('d-none justify-content-center')
    $('#search_game_btn').html('Search game')

    $('#search_game_form').removeClass('d-none')
    $('#game_state_buttons').addClass('d-none')

    //removeTimer('first_move_timer')
    //removeTimer('opp_disconnected_timer')

    clockPair.stop()

    /*
    var result = data.result
    var reason = data.reason

    var ratingDelta = null
    if (result === 'won') ratingDelta = ratingChanges.win
    else if (result === 'draw') ratingDelta = ratingChanges.draw
    else if (result === 'lost') ratingDelta = ratingChanges.lose
    else ratingDelta = 0

    rating += ratingDelta

    if (ratingDelta) {
      updateRating()
    }

    playGameEndedSound()
    declineDrawOfferLocally()
    */
    game_finished = true
  }

  function onFirstMoveWaiting(data) {
    var waitTime = data.wait_time
    //addFirstMoveTimer(waitTime)
  }

  function onOppDisconnected(data) {
    var waitTime = data.wait_time

    if ($('#opp_disconnected_timer').length === 0) {
      addOppDisconnectedTimer(waitTime)
    }
  }

  function onOppReconnected() {
    removeTimer('opp_disconnected_timer')
  }

  function searchGame() {
    var minutes = parseInt($('#search_game_time').val())
    sio.emit('search_game', {'minutes': minutes})
    $('#search_game_btn').html('Stop search')
    $('#search_game_form').prop('inSearch', true)
    $('#search_game_time').addClass('d-none')
    $('#search_spinner').addClass('d-flex justify-content-center')
      .removeClass('d-none')
    localStorage.lastGameTimeValue = minutes
  }

  function cancelSearch() {
    sio.emit('cancel_search')
    $('#search_game_btn').html('Search game')
    $('#search_game_time').removeClass('d-none')
    $('#search_game_form').prop('inSearch', false)
    $('#search_spinner').removeClass('d-flex justify-content-center')
      .addClass('d-none')
  }

  function onDrawOffer() {
    $('#draw_btn').prop('accept', true)
    $('#draw_btn').html('Accept a draw offer')
    playDrawOfferSound()

  }

  function onDrawOfferAccepted() {
  }

  function onDrawOfferDeclined() {
  }

  function acceptDrawOffer() {
    sio.emit('accept_draw_offer')
  }

  function makeDrawOffer() {
    sio.emit('make_draw_offer')
    $('#draw_btn').prop('disabled', true)
  }

  function declineDrawOfferLocally() {
    $('#draw_btn').html('Offer a draw')
    $('#draw_btn').prop('accept', false)
  }

  function updateBoardSize() {
    var viewportWidth = window.innerWidth - $('#right_container').width()
    var viewportHeight = window.innerHeight

    var containerSize = Math.floor(Math.min(viewportWidth / 10 * 8,
                                            viewportHeight / 10 * 8))
    containerSize -= containerSize % 8 - 1
    $board.width(containerSize)
    $board.height(containerSize)
    board.resize()
    if (moveIndx >= 0)
      highlightLastMove()
  }

  var config = {
    pieceTheme: '../static/img/pieces/{piece}.svg',
    draggable: true,
    onDragStart: onDragStart,
    onDrop: onDrop,
    highlight: true,
    highlight1: 'highlight-from',
    highlight2: 'highlight-to'
  }

  board = Chessboard('board', config)

  $(window).on('load', function() {
    if (localStorage.lastGameTimeValue) {
      $('#search_game_time').val(localStorage.lastGameTimeValue)
    }
  })

  $(window).on('load', updateBoardSize)
  $(window).resize(updateBoardSize)

  var href = window.location.href
  var game_id = href.slice(href.lastIndexOf('/') + 1)

  var sio = io({
    transports: ['websocket'],
    upgrade: false,
    query: {game_id: game_id},
  })

  sio.on('game_started', onGameStarted)
  sio.on('game_updated', onGameUpdated)
  sio.on('game_ended', onGameEnded)
  sio.on('redirect', function(data) {
    window.location.href = data.url
  })
  //sio.on('get_message', onGetMessage)
  //sio.on('first_move_waiting', onFirstMoveWaiting)
  //sio.on('opp_disconnected', onOppDisconnected)
  //sio.on('opp_reconnected', onOppReconnected)
  //sio.on('draw_offer', onDrawOffer)
  //sio.on('draw_offer_accepted', onDrawOfferAccepted)
  //sio.on('draw_offer_declined', onDrawOfferDeclined)

  $('#search_game_form').on('submit', function(e) {
    e.preventDefault()

    if ($('#search_game_form').prop('inSearch')) {
      cancelSearch()
    } else {
      searchGame()
    }
  })

  $('#message_form').on('submit', function(e) {
    e.preventDefault()
    sendMessage()
  })

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
    if (game !== null && moveIndx >= 0) {
      $movesList.find(`#move_${moveIndx}`).removeClass('halfmove-active')
      moveIndx -= 1
      game.undo()
      board.position(game.fen())
			$moveCell = $movesList.find(`#move_${moveIndx}`)
      $moveCell.addClass('halfmove-active')
			$movesList.scrollTop(Math.trunc(moveIndx / 2) * $moveCell.height())
      playMoveSound()

      removeHighlights()
      if (moveIndx >= 0)
        highlightLastMove()
    }
  }

  function moveForward() {
    if (game !== null && moveIndx + 1 !== movesArray.length) {
      $movesList.find(`#move_${moveIndx}`).removeClass('halfmove-active')
      moveIndx += 1
      game.move(movesArray[moveIndx])
      board.position(game.fen())
      $moveCell = $movesList.find(`#move_${moveIndx}`)
      $moveCell.addClass('halfmove-active')
			$movesList.scrollTop(Math.max(0, Math.trunc(moveIndx / 2) - 4) * $moveCell.height())
      playMoveSound()

      removeHighlights()
      highlightLastMove()
    }
  }

  function moveToBegin() {
    if (game !== null) {
      $movesList.find(`#move_${moveIndx}`).removeClass('halfmove-active')
      moveIndx = -1
      game.reset();
      board.position(game.fen())
      $movesList.scrollTop(0)
      playMoveSound()

      removeHighlights()
    }
  }

  function moveToEnd() {
    if (game !== null) {
      $movesList.find(`#move_${moveIndx}`).removeClass('halfmove-active')
      while (moveIndx + 1 !== movesArray.length) {
        moveIndx += 1
        game.move(movesArray[moveIndx])
      }
      board.position(game.fen())
      $movesList.find(`#move_${moveIndx}`).addClass('halfmove-active')
      $movesList.scrollTop($movesList[0].scrollHeight)
      playMoveSound()

      removeHighlights()
      highlightLastMove()
    }
  }

  $(document).keydown(function(e) {
    if (e.keyCode === 37) moveBack() // left arrow
    else if (e.keyCode === 39) moveForward()  // right arrow
    else if (e.keyCode === 38) moveToBegin()  // up arrow
    else if (e.keyCode === 40) moveToEnd()  // down arrow
  });

  function pushToMovesList(move, indx) {
    $movesList.find('.halfmove').removeClass('halfmove-active')
    if (game.turn() === 'w') {
      $movesList.append(`<div class="row move">
                          <div id="move_${indx}"
                               class="col halfmove halfmove-active">
                            ${move}
                          </div>
                          <div class="col"></div>
                         </div>`)
    } else {
      $moveCell = $movesList.children().last().children().last()
      $moveCell.attr('id', `move_${indx}`)
      $moveCell.addClass('halfmove halfmove-active')
      $moveCell.append(move)
    }
    $movesList.scrollTop($movesList[0].scrollHeight)
  }

  $('body').on('click', '.halfmove', function() {
    $movesList.find(`#move_${moveIndx}`).removeClass('halfmove-active')
    newMoveIndx = this.id.slice(5)
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
  })
})()
