(() => {
  const normalize = value => String(value || '').toLowerCase().replace(/ё/g, 'е').replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
  // Match the product itself, not a flavour (chips with mushrooms are still chips).
  const rules = [
    [/^(?:опята|грибы|шампиньоны|лук|огурцы|огурчики|корнишоны|томаты|помидоры|капуста) .*?(?:маринован|солен|квашен|консерв)/u, ['Консервы/соленья']],
    [/^(?:оливки|маслины|корнишоны)(?: |$)/u, ['Консервы/соленья']],
    [/^(?:горошек|кукуруза|фасоль) .*?консерв/u, ['Консервы/соленья']],
    [/^чипсы(?: |$)/u, ['Чипсы']],
    [/^(?:сырок|сырки) плавлен/u, ['Молочка/Сыры']],
    [/^(?:сырок|сырки)(?: |$)|^десерт творожный глазированный(?: |$)/u, ['Глазированные сырки', 'Молочка/Сыры']],
    [/^(?:молоко|кефир|йогурт|сметана|творог|сыр|масло сливочное|масло сладкосливочное)(?: |$)/u, ['Молочка/Сыры']],
    [/^(?:хлеб|батон|багет|булочка|булка|лаваш)(?: |$)/u, ['Хлебобулочные']],
    [/^(?:макароны|рис|гречка|крупа)(?: |$)/u, ['Крупы/макароны']],
    [/^яйца куриные(?: |$)/u, ['Яйца']],
    [/^лапша .*?(?:быстрого приготовления|ролтон|роллтон|доширак|биг бон|big bon|анаком|биг ланч)/u, ['Быстрое приготовление']],
    [/^(?:кофе|чай)(?: |$)/u, ['Чай/кофе']],
    [/^(?:кетчуп|майонез|горчица|соус)(?: |$)/u, ['Соусы']],
    [/^(?:конфеты|шоколад|зефир|печенье|мармелад|вафли|пряники|драже)(?: |$)/u, ['Сладости']],
    [/^(?:колбаса|сосиски|сардельки|ветчина|бекон)(?: |$)/u, ['Мясные изделия']],
    [/^(?:сельдь|семга|лосось|скумбрия|килька|креветки|кальмар|мидии|крабовые палочки|палочки крабовые|консервы рыбные)(?: |$)/u, ['Рыба/Морепродукты']],
    [/^(?:пельмени|вареники)(?: |$)/u, ['Замороженные полуфабрикаты', 'Полуфабрикаты']],
    [/^(?:онигири|суши)(?: |$)/u, ['Готовая еда']],
    [/^(?:лук|морковь|картофель|укроп|петрушка|перец свежий)(?: |$)/u, ['Овощи']],
    [/^(?:яблоки|бананы|апельсины|мандарины|груши|виноград|киви|лимоны)(?: |$)/u, ['Фрукты']],
  ];
  function suggest(name, categories, products = []) {
    const text = normalize(name);
    if (!text) return null;
    const available = categories.filter(c => c.kind === 'expense' && !c.is_archived);
    const ids = new Set(available.map(c => Number(c.id)));
    const words = text.match(/\p{L}+/gu) || [];
    // At least two leading words must agree; brand or flavour alone is not evidence.
    const similar = words.length >= 2 ? products.filter(p => {
      const other = normalize(p.name).match(/\p{L}+/gu) || [];
      return !p.is_archived && words[0] === other[0] && words[1] === other[1];
    }) : [];
    const known = new Set(similar.map(p => Number(p.category_id)));
    const byRule = rules.find(([pattern]) => pattern.test(text));
    const ruleCategory = byRule?.[1].map(n => available.filter(c => normalize(c.name) === normalize(n))).find(matches => matches.length === 1)?.[0];
    // A specific product rule wins over older, broad catalogue classifications.
    if (ruleCategory) return {id:Number(ruleCategory.id), reason:'По названию товара'};
    if (similar.length && known.size === 1 && ids.has([...known][0])) {
      return {id:[...known][0], reason:'По похожим товарам в вашем каталоге'};
    }
    return null;
  }
  function resolve(row, categories, products) {
    if (row.category_touched) return {id:row.category_id || null};
    if (row.catalog) return {id:row.catalog.category_id || null};
    return suggest(row.name, categories, products) || {id:null};
  }
  window.App.receiptCategories = {suggest, resolve};
})();
