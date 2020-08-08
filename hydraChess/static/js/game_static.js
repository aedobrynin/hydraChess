;(function() {
  var board = null
  var $board = $('#board')

  var game = null

  var $movesList = $('#moves_list')
  var movesArray = null
  var moveIndx = null

  var animation = false

  /* -- GAME INFO RELATED FUNCTIONS -- */

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

      containerSize = Math.floor(
        Math.min(
          viewportWidth / 10 * 8,
          viewportHeight / 10 * 8
        )
      )
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
  }

  // should be called before EVERY animation
  function blockAnimation() {
    animation = true
    setTimeout(function() { animation = false }, config.moveSpeed + 30)
  }

  var config = {
    pieceTheme: '../static/img/pieces/{piece}.svg',
    draggable: true,
    onDragStart: function() { return false },
    onChange: blockAnimation,
    highlight: true,
    highlight1: 'highlight-from',
    highlight2: 'highlight-to',
    moveSpeed: 200
  }

  board = Chessboard('board', config)

  $(window).on('load', checkOrientation)
  $(window).resize(checkOrientation)

  $(window).on('load', updateBoardSize)
  $(window).resize(updateBoardSize)

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


  function setGameData(data) {
    console.log(data.game)
    data = data.game

    if (data.moves !== '') {
      movesArray = data.moves.split(',')
    } else {
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

    if (data.color === 'w') {
      setPlayersInfo(data.black_user, data.white_user);
    } else {
      board.orientation('black')
      setPlayersInfo(data.white_user, data.black_user);
    }

    setResults(data.result)
  }

  $.get(
    '/api/v1.x/game',
    {
      id: parseInt(location.href.split('/').slice(-1)[0])
    },
    setGameData,
  )
})()
