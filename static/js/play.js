;(function () {
  var board = null
  var $board = $("#main_board")
  var color = null
  var game = new Chess()
  var nickname = null
  var rating = null
  var rating_changes = null


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


  function onGetMessage(data) {
    message = `<b>${data.sender}</b>: ${data.message}<br>`
    document.getElementById("messages_box").innerHTML += message
    $("#messages_box").scrollTop($("#messages_box")[0].scrollHeight)
  }


  function notificationMessage(message) {
    document.getElementById("messages_box").innerHTML += message
    $("#messages_box").scrollTop($("#messages_box")[0].scrollHeight)
  }


  function updateRating() {
    document.getElementById("own_rating").innerHTML = `(${rating})`
  }


  function onDragStart(source, piece, position, orientation) {
    if (game.game_over() || color[0] != piece[0]) return false
  }


  function onDrop(source, target) {
    if (color[0] != game.turn()) return 'snapback'

    var move = game.move({
      from: source,
      to: target,
      promotion: 'q' // NOTE: always promote to a queen for example simplicity
    })

    // illegal move
    if (move === null) return 'snapback'

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
    game.load(data.fen)
    board.position(game.fen())
    board.orientation(data.color)
    color = data.color
    rating_changes = data.rating_changes
    opp_nickname = data.opp_nickname
    opp_rating = data.opp_rating
    document.getElementById("opp_nickname").innerHTML = opp_nickname
    document.getElementById("opp_rating").innerHTML = `(${opp_rating})`

    $('#find_game_btn').prop('disabled', true)
    $('#message_input').prop('readonly', false)

    message = `<div class="notification">
                        <div class="notification-game-state">NEW GAME</div>
                        <span class="notification-nickname">${nickname}</span> (${rating}) VS
                        <span class="notification-nickname">${opp_nickname}</span> (${opp_rating})<br>
                        win +${rating_changes.win} / draw ${(rating_changes.draw <= 0 ? "" : "+") + rating_changes.draw} / lose ${rating_changes.lose}
                   </div>`
    notificationMessage(message)
  }

  function onGameUpdated(data) {
    game.move(data.san)
    board.position(game.fen())
  }


  function onGameEnded(data) {
    result = data.result
    rating_delta = null
    if (result == 'won') rating_delta = rating_changes.win
    else if (result == 'draw') rating_delta = rating_changes.draw
    else if (result == 'lost') rating_delta = rating_changes.lose

    rating += rating_delta

    if (rating_delta) {
      updateRating()
    }

    $('#find_game_btn').prop('disabled', false)
    $('#message_input').prop('readonly', true)

    message = `<div class="notification">
                        <div class="notification-game-state">GAME ${result.toUpperCase()}</div>
                        Your new rating: ${rating} (${(rating_delta <= 0 ? "" : "+") + rating_delta})
                   </div>`
    notificationMessage(message)
  }


  function searchGame()
  {
    sio.emit('search')
    $('#find_game_btn').prop('disabled', true)
  }


  var config = {
    pieceTheme: 'static/img/{piece}.svg',
    draggable: true,
    onDragStart: onDragStart,
    onDrop: onDrop
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


  window.searchGame = searchGame
  window.sendMessage = sendMessage
})()
