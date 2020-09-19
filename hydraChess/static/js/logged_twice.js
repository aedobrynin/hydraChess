export function showLoggedTwiceModal() {
  $('body').append(`
    <div id="logged_twice_modal" class="modal" id="modal" tabindex="-1"
         role="dialog" aria-hidden="true">
      <div class='modal-background'></div>
      <div class='modal-content'>
        <div class='box mx-6'>
          <div class='columns is-mobile is-centered has-text-centered'>
            <div class='column is-narrow' style='font-size: 20px'>
              You have logged in on another page.<br>
              Reload this page to continue here.
            </div>
          </div>
          <div class='columns is-mobile is-centered'>
            <div class='column is-narrow'>
              <button class='button is-primary is-outlined'
                      onclick='location.reload()'>Reload page</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  `)
  $('#logged_twice_modal').addClass('animate__animated animate__fadeIn is-active')
}
