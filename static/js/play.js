;(function () {
  var board = null
  var $board = $("#main_board")
  var color = null
  var game = null
  var nickname = null
  var rating = null
  var rating_changes = null


  function getFullmoveNumber() {
    if (game == null) return 0
    var fen = game.fen()
    var fullmoveNumber = parseInt(fen.split(' ')[5])
    return fullmoveNumber
  }

  function messagesBoxResize() {
    width = $(window).width()

    if (width >= 1200) {
      $('#messages_box').css({'height': '692px',
        'max-height': '692px'})
    }
    else if (width >= 992)
    {
      $('#messages_box').css({'height': '572px',
        'max-height': '572px'})
    }
    else
    {
      $('#messages_box').css({'height': '100px',
        'max-height': '100px'})
    }
  }

  function sendMessage() {
    message = document.getElementById("message_input").value.trim()
    document.getElementById("message_input").value = ""
    if (message == "") return

    sio.emit('send_message', {'message': message})
  }


  function pushNotification(message) {
    document.getElementById("messages_box").innerHTML += message
    $("#messages_box").scrollTop($("#messages_box")[0].scrollHeight)
  }

  function onGetMessage(data) {
    message = `<span class="notification-nickname">${data.sender}</span>: ${data.message}<br>`
    pushNotification(message)
  }

  function updateRating() {
    document.getElementById("own_rating").innerHTML = `(${rating})`
  }

  function getPosByPiece(piece) {
    var board = game.board();
    var b_conc = [].concat(...board)
    var indexes = b_conc.map((p, indx) => {
      if (p !== null && p.type === piece.type && p.color === piece.color) {
        return indx
      }
    }).filter(val => val !== undefined)

    var positions = indexes.map((cell_index) => {
      const row = 'abcdefgh'[cell_index % 8]
      const col = Math.ceil((64 - cell_index) / 8)
      return row + col
    })

    return positions
  }


  function removeHighlights() {
    $board.find('.square-55d63')
      .removeClass('highlight-move-source')
      .removeClass('highlight-move-target')
      .removeClass('highlight-check')
  }


  function addHighlights(source, target) {
    $board.find('.square-' + source).addClass('highlight-move-source')
    $board.find('.square-' + target).addClass('highlight-move-target')
  }


  function highlightChecked() {
    piece = {type: 'k', color: game.turn()}
    pos = getPosByPiece(piece)[0]
    console.log(pos)

    $board.find('.square-' + pos).addClass('highlight-check')
  }


  function onDragStart(source, piece, position, orientation) {
    if (game == null || game.game_over() || color != piece[0]) return false
  }


  function onDrop(source, target) {
    if (game == null) return 'snapback'
    if (color != game.turn()) return 'snapback'

    var move = game.move({
      from: source,
      to: target,
      promotion: 'q' // TODO
    })

    // illegal move
    if (move === null) return 'snapback'


    removeHighlights()
    removeTimer('first-move-timer')

    if (game.in_check()) {
      highlightChecked()
    }
    addHighlights(source, target)

    game.undo()

    sio.emit('move', {"san": move.san})
  }


  function onSetData(data) {
    if ('nickname' in data) {
      nickname = data.nickname
      document.getElementById("own_nickname").innerHTML = data.nickname
    }

    if ('rating' in data) {
      rating = data.rating
      updateRating()
    }
  }


  function onGameStarted(data) {
    removeHighlights()

    game = new Chess(data.fen)
    board.position(game.fen())

    color = data.color
    if (color == 'w')
      board.orientation('white')
    else
      board.orientation('black')

    rating_changes = data.rating_changes
    opp_nickname = data.opp_nickname
    opp_rating = data.opp_rating
    document.getElementById("opp_nickname").innerHTML = opp_nickname
    document.getElementById("opp_rating").innerHTML = `(${opp_rating})`

    $('#find_game_btn').prop('disabled', true)
    $('#message_input').prop('readonly', false)


    notification = `<div class="notification">
                      <div class="notification-game-state">NEW GAME</div>
                      <span class="notification-nickname">${nickname}</span> (${rating}) VS
                      <span class="notification-nickname">${opp_nickname}</span> (${opp_rating})<br>
                      <span class="rating-changes">
                        win +${rating_changes.win} / draw ${(rating_changes.draw <= 0 ? "" : "+") + rating_changes.draw} / lose ${rating_changes.lose}
                      </span>
                    </div>`

    if (document.getElementById("messages_box").innerHTML.length != 0)
      notification = '<br>' + notification

    pushNotification(notification)
  }

  function addFirstMoveTimer(waitTime) {
    notification = `<div class="notification">
                      <div class="timer-container" id="first-move-timer">
                        You have <span class="timer">${waitTime}</span> seconds for your first move
                      </div>
                    </div>`

    pushNotification(notification)
    setTimeout(updateTimer, 1000, "first-move-timer")
  }


  function addOppDisconnectedTimer(waitTime) {
    notification = `<div class="notification">
                      <div class="timer-container" id="opp-disconnected-timer">
                        Opponent has <span class="timer">${waitTime}</span> seconds to reconnect
                      </div>
                    </div>`

    pushNotification(notification)
    setTimeout(updateTimer, 1000, "opp-disconnected-timer")
  }


  function updateTimer(timerId) {
    var $timer = $("#" + timerId).find('.timer')

    if ($timer.length == 0) return

    cur_value = parseInt($timer.html())

    if (cur_value == 0) removeTimer(timerId)
    else {
      $timer.html(cur_value - 1)
      setTimeout(updateTimer, 1000, timerId)
    }
  }

  function removeTimer(timerId) {
    $("#" + timerId).parent().remove()
  }

  function onGameUpdated(data) {
    move = game.move(data.san)

    removeHighlights()
    addHighlights(move.from, move.to)
    if (game.in_check()) {
      highlightChecked()
    }

    board.position(game.fen())
  }

  function onGameEnded(data) {
    removeTimer('first-move-timer')
    removeTimer('opp-disconnected-timer')

    result = data.result
    reason = data.reason
    rating_delta = null
    if (result == 'won') rating_delta = rating_changes.win
    else if (result == 'draw') rating_delta = rating_changes.draw
    else if (result == 'lost') rating_delta = rating_changes.lose
    else rating_delta = 0

    rating += rating_delta

    if (rating_delta) {
      updateRating()
    }

    $('#find_game_btn').prop('disabled', false)
    $('#message_input').prop('readonly', true)

    notification = `<div class="notification">
                      <div class="notification-game-state">GAME ${result.toUpperCase()}</div>
                      <div class="notification-res-reason">${reason}</div>
                      <span class="new-rating">New rating: ${rating} (${(rating_delta <= 0 ? "" : "+") + rating_delta})</span>
                    </div>`
    pushNotification(notification)

    game = null
  }

  function onFirstMoveWaiting(data) {
    var waitTime = data.wait_time
    addFirstMoveTimer(waitTime)
  }

  function onOppDisconnected(data) {
    var waitTime = data.wait_time
    addOppDisconnectedTimer(waitTime)
  }

  function onOppReconnected() {
    removeTimer('opp-disconnected-timer')
  }

  function searchGame() {
    sio.emit('search')
    $('#find_game_btn').prop('disabled', true)
  }


  var config = {
    pieceTheme: 'static/img/{piece}.svg',
    draggable: true,
    onDragStart: onDragStart,
    onDrop: onDrop,
    highlight: true,
    highlight1: 'highlight-source',
    highlight2: 'highlight-target'
  }

  var board = Chessboard('main_board', config)
  $(window).resize(board.resize)
  $(document).ready(messagesBoxResize)
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


  window.searchGame = searchGame
  window.sendMessage = sendMessage
})()
