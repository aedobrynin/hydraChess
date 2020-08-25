;(function() {
  var timeData = [
    {name: '1 minute', minutes: 1},
    {name: '2 minutes', minutes: 2},
    {name: '3 minutes', minutes: 3},
    {name: '5 minutes', minutes: 5},
    {name: '10 minutes', minutes: 10},
    {name: '15 minutes', minutes: 15},
    {name: '30 minutes', minutes: 30},
    {name: '1 hour', minutes: 60},
    {name: '2 hours', minutes: 120}
  ]

  var $select = $('#mobile_time_select')
  var buttons = $('#buttons_tablet').find('.button')
  var $modal = $('#active_search_modal')

  // Fill the buttons
  buttons.each(function(index) {
    $(this).html(timeData[index].name)
    $(this).attr('minutes', timeData[index].minutes)
  })

  // Fill the select for mobile screens
  timeData.forEach(function(data) {
    $select
      .append($('<option></option>')
                .attr('value', data.minutes)
                .text(data.name))
  })

  var sio = io({
    transports: ['websocket'],
    upgrade: false,
    query: {request_type: 'lobby'}
  })

  sio.on('redirect', function(data) {
    window.location.href = data.url
  })


  $('body').on('click', 'button[minutes]', function() {
    searchGame(parseInt($(this).attr('minutes')))
  })


  $('#start_searching').on('click', function() {
    searchGame(parseInt($select.val()))
  })

  $('#cancel_search_button').on('click', cancelSearch)

  function searchGame(minutes) {
    $modal.addClass('animate__animated animate__fadeIn is-active')
    sio.emit('search_game', {minutes: minutes})
  }

  function cancelSearch() {
    $modal.addClass('animate__fadeOut')
    setTimeout(
      function() {
        $modal
          .removeClass('animate__animated animate__fadeOut animate__fadeIn is-active')

        },
      110
    )
    sio.emit('cancel_search')
  }
})()
