;(function() {
  var board = null
  var $board = $('#main_board')
  var color = null
  var game = null
  var nickname = null
  var rating = null
  var ratingChanges = null

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
  function messagesBoxResize() {
    var width = $(window).width()

    if (width >= 1200) {
      $('#messages_box').css({'height': '630px',
        'max-height': '630px'})
    } else if (width >= 992) {
      $('#messages_box').css({'height': '510px',
        'max-height': '510px'})
    } else {
      $('#messages_box').css({'height': '100px',
        'max-height': '100px'})
    }
  }

  function sendMessage() {
    var message = $('#message_input').val().trim()
    $('#message_input').val('')
    if (message === '') return

    sio.emit('send_message', {'message': message})
  }

  function pushNotification(message) {
    $('#messages_box').append(message)
    $('#messages_box').scrollTop($('#messages_box')[0].scrollHeight)
  }

  function onGetMessage(data) {
    var message = `<span class='notification-nickname'>${data.sender}</span>:` +
                  `${data.message}<br>`
    pushNotification(message)
  }
  /* -- CHAT RELATED FUNCTIONS -- */

  /* -- HIGHLIGHTS RELATED FUNCTIONS -- */
  function removeHighlights() {
    $board.find('.square-55d63')
      .removeClass('highlight-move-source')
      .removeClass('highlight-move-target')
      .removeClass('highlight-check')
  }

  function addHighlights(source, target) {
    console.log(source, target)
    $board.find('.square-' + source).addClass('highlight-move-source')
    $board.find('.square-' + target).addClass('highlight-move-target')
  }

  function highlightChecked() {
    var piece = {type: 'k', color: game.turn()}
    var pos = getPosByPiece(piece)[0]

    $board.find('.square-' + pos).addClass('highlight-check')
  }
  /* -- HIGHLIGHTS RELATED FUNCTIONS -- */

  /* -- TIMERS RELATED FUNCTIONS -- */
  function addFirstMoveTimer(waitTime) {
    var notification = '' +
      `<div class='notification'>
         <div class='timer-container' id='first_move_timer'>
           You have <span class="timer">${waitTime}</span> seconds for your first move
         </div>
       </div>`

    pushNotification(notification)
    setTimeout(updateTimer, 1000, 'first_move_timer')
  }

  function addOppDisconnectedTimer(waitTime) {
    var notification = '' +
      `<div class='notification'>
         <div class='timer-container' id='opp_disconnected_timer'>
           Opponent has <span class="timer">${waitTime}</span> seconds to reconnect
         </div>
       </div>`

    pushNotification(notification)
    setTimeout(updateTimer, 1000, 'opp_disconnected_timer')
  }

  function updateTimer(timerId) {
    var $timer = $('#' + timerId).find('.timer')

    if ($timer.length === 0) return

    var curValue = parseInt($timer.html())

    if (curValue === 0) removeTimer(timerId)
    else {
      $timer.html(curValue - 1)
      setTimeout(updateTimer, 1000, timerId)
    }
  }

  function removeTimer(timerId) {
    $('#' + timerId).parent().remove()
  }
  /* -- TIMERS RELATED FUNCTIONS -- */

  /* -- CLOCKS RELATED FUNCTIONS -- */

  function addLeadingZero(value) {
    if (value < 10) return '0' + value
    return value.toString()
  }

  function setClocks(oppClock, ownClock) {
    if (oppClock) {
      oppClock.min = addLeadingZero(oppClock.min)
      oppClock.sec = addLeadingZero(oppClock.sec)

      var $oppClock = $('#opp_clock')
      $oppClock.find('.min').html(oppClock.min)
      $oppClock.find('.sec').html(oppClock.sec)
    }

    if (ownClock) {
      ownClock.min = addLeadingZero(ownClock.min)
      ownClock.sec = addLeadingZero(ownClock.sec)

      var $ownClock = $('#own_clock')
      $ownClock.find('.min').html(ownClock.min)
      $ownClock.find('.sec').html(ownClock.sec)
    }
  }

  function updateClock(user) {
    var $clock = $(`#${user}_clock`)
    var $min = $clock.find('.min')
    var $sec = $clock.find('.sec')

    var min = parseInt($min.html())
    var sec = parseInt($sec.html())
    if (sec > 0) {
      sec -= 1
      $sec.html(addLeadingZero(sec))
    } else if (min > 0) {
      min -= 1
      $min.html(addLeadingZero(min))
      $sec.html('59')
    }
  }

  function updateClocks() {
    if (game == null) return

    if (color === game.turn()) {
      updateClock('own')
    } else {
      updateClock('opp')
    }
    setTimeout(updateClocks, 1000)
  }
  /* -- CLOCKS RELATED FUNCTIONS -- */

  function updateRating() {
    $('#own_rating').html(`(${rating})`)
  }

  function onDragStart(source, piece, position, orientation) {
    if (game == null || game.game_over() || color !== piece[0]) return false
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

    removeHighlights()
    removeTimer('first_move_timer')

    if (game.in_check()) {
      highlightChecked()
    }

    if (!game.game_over()) {
      playMoveSound()
    }

    addHighlights(source, target)

    game.undo()

    sio.emit('make_move', {'san': move.san})
    declineDrawOfferLocally()
  }

  function onSetData(data) {
    if ('nickname' in data) {
      nickname = data.nickname
      $('#own_nickname').html(data.nickname)
    }

    if ('rating' in data) {
      rating = data.rating
      updateRating()
    }
  }

  function onGameStarted(data) {
    playGameStartedSound()

    setClocks(data.opp_clock, data.own_clock)

    game = new Chess(data.fen)
    board.position(game.fen())

    color = data.color
    if (color === 'w') {
      board.orientation('white')
    } else {
      board.orientation('black')
    }

    if (data.last_move) {
      console.log(data.last_move.slice(0, 2))
      addHighlights(data.last_move.slice(0, 2),
                    data.last_move.slice(2, 4))
    }

    if (game.in_check()) {
      highlightChecked()
    }

    // If game is started, start clocks
    if (!(getFullmoveNumber() === 1 && game.turn() === 'w')) {
      setTimeout(updateClocks, 1000)
    }

    ratingChanges = data.rating_changes
    var oppNickname = data.opp_nickname
    var oppRating = data.opp_rating
    $('#opp_nickname').html(oppNickname)
    $('#opp_rating').html(`(${oppRating})`)

    $('#message_input').prop('readonly', false)

    $('#search_game_form').addClass('d-none')
    $('#game_state_buttons').removeClass('d-none')

    var notification = '' +
      `<div class='notification'>
         <div class='notification-game-start'>NEW GAME</div>
         <span class='notification-nickname'>${nickname}</span> (${rating}) VS
         <span class='notification-nickname'>${oppNickname}</span> (${oppRating})
         <br>
         <span class='rating-changes'>
           win +${ratingChanges.win} / draw ${(ratingChanges.draw <= 0 ? '' : '+') + ratingChanges.draw} / lose ${ratingChanges.lose}
         </span>
       </div>`

    if ($('#messages_box').html().length !== 0) {
      notification = '<br>' + notification
    }

    pushNotification(notification)

    $('#draw_btn').html('Offer a draw')
    $('#draw_btn').prop('accept', false)
    $('#draw_btn').prop('disabled', !data.can_send_draw_offer)
  }

  function onGameUpdated(data) {
    setClocks(data.opp_clock, data.own_clock)

    var move = game.move(data.san)

    if (getFullmoveNumber() === 1) {
      setTimeout(updateClocks, 1000)
    }

    board.position(game.fen())

    removeHighlights()
    addHighlights(move.from, move.to)
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
    $('#find_game_btn').prop('disabled', false)
    $('#game_time').prop('disabled', false)
    $('#message_input').prop('readonly', true)

    $('#search_game_form').removeClass('d-none')
    $('#game_state_buttons').addClass('d-none')

    removeTimer('first_move_timer')
    removeTimer('opp_disconnected_timer')

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

    var notification = '' +
          `<div class='notification'>
             <div class='notification-game-state'>GAME ${result.toUpperCase()}</div>
             <div class='notification-res-reason'>${reason}</div>
             <span class='new-rating'>New rating: ${rating} (${(ratingDelta <= 0 ? '' : '+') + ratingDelta})</span>
           </div>`
    pushNotification(notification)

    playGameEndedSound()
    declineDrawOfferLocally()

    game = null
  }

  function onFirstMoveWaiting(data) {
    var waitTime = data.wait_time
    addFirstMoveTimer(waitTime)
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
    var minutes = parseInt($('#game_time').val())
    sio.emit('search', {'minutes': minutes})
    $('#find_game_btn').prop('disabled', true)
    $('#game_time').prop('disabled', true)

    localStorage.lastGameTimeValue = minutes
  }

  function onDrawOffer() {
    $('#draw_btn').prop('accept', true)
    $('#draw_btn').html('Accept a draw offer')
    playDrawOfferSound()

    var notification = `<div class="notification">
                          You've got a draw offer
                        </div>`
    pushNotification(notification)
  }

  function onDrawOfferAccepted() {
    var notification = `<div class="notification">
                          Draw offer was accepted
                        </div>`
    pushNotification(notification)
  }

  function onDrawOfferDeclined() {
    var notification = `<div class="notification">
                          Draw offer was declined
                        </div>`
    pushNotification(notification)
  }

  function acceptDrawOffer() {
    sio.emit('accept_draw_offer')
  }

  function makeDrawOffer() {
    sio.emit('make_draw_offer')
    $('#draw_btn').prop('disabled', true)

    var notification = `<div class="notification">
                          Draw offer was sent
                        </div>`
    pushNotification(notification)
  }

  function declineDrawOfferLocally() {
    $('#draw_btn').html('Offer a draw')
    $('#draw_btn').prop('accept', false)
  }

  var config = {
    pieceTheme: 'static/img/pieces/{piece}.svg',
    draggable: true,
    onDragStart: onDragStart,
    onDrop: onDrop,
    highlight: true,
    highlight1: 'highlight-source',
    highlight2: 'highlight-target'
  }

  board = Chessboard('main_board', config)
  $(window).resize(board.resize)
  $(document).ready(messagesBoxResize)
  $(document).ready(function() {
    if (localStorage.lastGameTimeValue) {
      $('#game_time').val(localStorage.lastGameTimeValue)
    }
  })
  $(window).resize(messagesBoxResize)

  var sio = io({transports: ['websocket'], upgrade: false})
  sio.on('game_started', onGameStarted)
  sio.on('game_updated', onGameUpdated)
  sio.on('game_ended', onGameEnded)
  sio.on('set_data', onSetData)
  sio.on('get_message', onGetMessage)
  sio.on('first_move_waiting', onFirstMoveWaiting)
  sio.on('opp_disconnected', onOppDisconnected)
  sio.on('opp_reconnected', onOppReconnected)
  sio.on('draw_offer', onDrawOffer)
  sio.on('draw_offer_accepted', onDrawOfferAccepted)
  sio.on('draw_offer_declined', onDrawOfferDeclined)

  $('#search_game_form').on('submit', function(e) {
    e.preventDefault()
    searchGame()
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
})()
