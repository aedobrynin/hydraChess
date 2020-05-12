;(function() {
  var sliderValues = [1, 2, 3, 5, 10, 20, 30, 60];

  var $slider = $('#slider_minutes'),
      $minutesInfo = $('#minutes_info'),
      $findGameBtn = $('#find_game_btn'),
      $stopSearchBtn = $('#stop_search_btn');

  $slider.on('input', function(){
    var minutes = sliderValues[this.value]
    var word = "minute"
    if (minutes !== 1)
      word += 's'
    $minutesInfo.html(`${minutes} ${word}`)
  })

  if (localStorage.lastGameTimeValue) {
    $slider.val(localStorage.lastGameTimeValue)
  }
  $slider.trigger('input');

  var sio = io({
    transports: ['websocket'],
    upgrade: false})

  sio.on('redirect', function(data) {
    window.location.href = data.url
  })

  function searchGame() {
    var gameTime = sliderValues[$slider.val()]
    localStorage.lastGameTimeValue = $slider.val()
    sio.emit('search_game', {minutes: gameTime})
    $slider.attr('disabled', true)
    $findGameBtn.css('display', 'none')
    $stopSearchBtn.css('display', '')
  }

  function cancelSearch() {
    sio.emit('cancel_search')
    $slider.attr('disabled', false)
    $findGameBtn.css('display', '')
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
