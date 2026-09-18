(function () {
  const lang = document.body?.dataset?.idioma || "pt-BR";
  if (lang === "pt-BR") return;

  const dict = {
    en: {
      "Menu":"Menu", "Calendário":"Calendar", "Sugestões e feedback":"Suggestions & feedback", "Configurações":"Settings", "Área profissional":"Professional area", "Sair da conta":"Log out",
      "Veja as próximas palestras e ações.":"See upcoming talks and activities.", "Ajude a melhorar o New ONGs.":"Help improve New ONGs.", "Gerencie sua conta e suas preferências.":"Manage your account and preferences.", "Acesso para profissionais e administração.":"Access for professionals and administration.", "Encerrar sua sessão.":"End your session.",
      "Pesquisar palestras, temas...":"Search talks, topics...", "DESTAQUE":"FEATURED", "Informação também é cuidado.":"Information is also care.", "Conteúdos educativos para você entender, aprender e se cuidar.":"Educational content to help you understand, learn and care for yourself.", "Explorar":"Explore", "Palestras":"Talks", "Ver tudo":"See all", "Notificações":"Notifications", "Chat":"Chat", "Perfil":"Profile", "Home":"Home", "Pesquisa":"Search", "Curtir":"Like", "Curtido":"Liked", "Salvar":"Save", "Salvo":"Saved",
      "Configurações":"Settings", "Personalize sua experiência no New ONGs.":"Customize your New ONGs experience.", "Conta":"Account", "Acessibilidade":"Accessibility", "Privacidade e segurança":"Privacy & security", "Ajuda":"Help", "Sobre o New ONGs":"About New ONGs", "Idioma":"Language",
      "Calendário":"Calendar", "Eventos do mês":"Events this month", "Nenhum evento cadastrado para este mês.":"No events scheduled for this month.", "Notificações gerais":"General notifications", "Nenhuma notificação no momento.":"No notifications at the moment."
    },
    es: {
      "Menu":"Menú", "Calendário":"Calendario", "Sugestões e feedback":"Sugerencias y comentarios", "Configurações":"Configuración", "Área profissional":"Área profesional", "Sair da conta":"Cerrar sesión", "Pesquisar palestras, temas...":"Buscar charlas, temas...", "DESTAQUE":"DESTACADO", "Informação também é cuidado.":"La información también es cuidado.", "Explorar":"Explorar", "Palestras":"Charlas", "Ver tudo":"Ver todo", "Notificações":"Notificaciones", "Chat":"Chat", "Perfil":"Perfil", "Home":"Inicio", "Pesquisa":"Buscar", "Curtir":"Me gusta", "Curtido":"Me gusta", "Salvar":"Guardar", "Salvo":"Guardado", "Acessibilidade":"Accesibilidad", "Privacidade e segurança":"Privacidad y seguridad", "Ajuda":"Ayuda", "Idioma":"Idioma", "Eventos do mês":"Eventos del mes", "Nenhum evento cadastrado para este mês.":"No hay eventos este mes.", "Nenhuma notificação no momento.":"No hay notificaciones en este momento."
    },
    fr: {"Menu":"Menu","Calendário":"Calendrier","Configurações":"Paramètres","Área profissional":"Espace professionnel","Sair da conta":"Se déconnecter","Notificações":"Notifications","Perfil":"Profil","Pesquisa":"Recherche","Palestras":"Conférences","Eventos do mês":"Événements du mois","Idioma":"Langue","Acessibilidade":"Accessibilité"},
    it: {"Menu":"Menu","Calendário":"Calendario","Configurações":"Impostazioni","Área profissional":"Area professionale","Sair da conta":"Esci","Notificações":"Notifiche","Perfil":"Profilo","Pesquisa":"Cerca","Palestras":"Conferenze","Eventos do mês":"Eventi del mese","Idioma":"Lingua","Acessibilidade":"Accessibilità"},
    de: {"Menu":"Menü","Calendário":"Kalender","Configurações":"Einstellungen","Área profissional":"Berufsbereich","Sair da conta":"Abmelden","Notificações":"Benachrichtigungen","Perfil":"Profil","Pesquisa":"Suche","Palestras":"Vorträge","Eventos do mês":"Veranstaltungen des Monats","Idioma":"Sprache","Acessibilidade":"Barrierefreiheit"},
    ja: {"Menu":"メニュー","Calendário":"カレンダー","Configurações":"設定","Área profissional":"専門家エリア","Sair da conta":"ログアウト","Notificações":"通知","Perfil":"プロフィール","Pesquisa":"検索","Palestras":"講演","Eventos do mês":"今月のイベント","Idioma":"言語","Acessibilidade":"アクセシビリティ"},
    ko: {"Menu":"메뉴","Calendário":"캘린더","Configurações":"설정","Área profissional":"전문가 영역","Sair da conta":"로그아웃","Notificações":"알림","Perfil":"프로필","Pesquisa":"검색","Palestras":"강연","Eventos do mês":"이번 달 행사","Idioma":"언어","Acessibilidade":"접근성"},
    "zh-CN": {"Menu":"菜单","Calendário":"日历","Configurações":"设置","Área profissional":"专业人员专区","Sair da conta":"退出登录","Notificações":"通知","Perfil":"个人资料","Pesquisa":"搜索","Palestras":"讲座","Eventos do mês":"本月活动","Idioma":"语言","Acessibilidade":"无障碍"}
  }[lang] || {};

  function translateElement(el) {
    if (el.children.length === 0) {
      const text = el.textContent.trim();
      if (dict[text]) el.textContent = dict[text];
    }
    if (el.placeholder && dict[el.placeholder]) el.placeholder = dict[el.placeholder];
    if (el.title && dict[el.title]) el.title = dict[el.title];
  }
  document.querySelectorAll("h1,h2,h3,h4,p,small,strong,span,a,button,label,input,textarea,option").forEach(translateElement);
  document.documentElement.lang = lang;
})();
