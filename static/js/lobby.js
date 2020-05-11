;(function() {
  var sliderValues = [1, 2, 3, 5, 10, 20, 30, 60];

  var $slider = $('#slider_minutes'),
      $minutesInfo = $('#minutes_info');

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
  }

  $('#find_game_form').on('submit', function(e) {
    e.preventDefault()
    searchGame()
  })

})()
