;(function() {
  var $minutesInfo = $('#minutes_info')
  var $findGameBtn = $('#find_game_btn')
  var $stopSearchBtn = $('#stop_search_btn')

  var sio = io({
    transports: ['websocket'],
    upgrade: false})

  sio.on('redirect', function(data) {
    window.location.href = data.url
  })

  function searchGame() {
    var gameTime = sliderValues[$slider.val()]
    sio.emit('search_game', {minutes: gameTime})
    $slider.attr('disabled', true)
    $findGameBtn.css('display', 'none')
    $stopSearchBtn.css('display', 'block')
  }

  function cancelSearch() {
    sio.emit('cancel_search')
    $slider.attr('disabled', false)
    $findGameBtn.css('display', 'block')
    $stopSearchBtn.css('display', 'none')
  }

  $findGameBtn.on('click', function(e) {
    e.preventDefault()
    searchGame()
  })

  $stopSearchBtn.on('click', function(e) {
    e.preventDefault()
    cancelSearch()
  })
})()
