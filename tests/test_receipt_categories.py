"""Conservative category proposals use only the current owner's expense categories."""
import subprocess
from pathlib import Path

MODULE = Path('static/js/app-receipt-categories.js').read_text()


def test_category_proposals_and_manual_priority():
    script = '''
const api=window.App.receiptCategories;
const names=['Консервы/соленья','Чипсы','Глазированные сырки','Овощи','Рыба/Морепродукты','Соусы','Крупы/макароны','Молочка/Сыры'];
const categories=names.map((name,i)=>({id:i+1,name,kind:'expense'}));
const cases=[
 ['Опята маринованные Лорадо 314мл',1],['Огурчики маринованные Микадо 370мл',1],
 ['Оливки без косточки 300г',1],['Горошек консервированный 400г',1],
 ['Чипсы Московский картофель маринованные огурцы 130г',2],
 ['Сырок плавленый Дружба 90г',8],['Соус грибной 200г',6],['Сырок соленая карамель 45г',3],
 ['Лук репчатый красный вес',4],['Консервы рыбные килька 220г',5],
 ['Горошек замороженный 400г',null],['Грибы свежие 200г',null],
 ['Неизвестный продукт',null],['',null],['Макароны Макфа 400г',7],
];
for(const [name,expected] of cases){
 const got=api.suggest(name,categories)?.id??null;
 if(got!==expected)throw Error(name+': '+got+' != '+expected);
}
const examples=[{name:'Напиток Лимонад 1л',category_id:4},{name:'Напиток Лимонад 2л',category_id:4}];
if(api.suggest('Напиток Лимонад новый 0.5л',categories,examples)?.id!==4)throw Error('catalogue');
examples.push({name:'Напиток Лимонад 3л',category_id:5});
if(api.suggest('Напиток Лимонад новый 0.5л',categories,examples))throw Error('ambiguous catalogue');
if(api.suggest('Лимонад 1л',categories,examples))throw Error('flavour alone');
if(api.suggest('Опята маринованные',categories.filter(c=>c.id!==1)))throw Error('missing category');
if(api.suggest('Опята маринованные',[{id:9,name:names[0],kind:'income'}]))throw Error('income');
const row={name:'Опята маринованные',category_touched:true,category_id:null,price:789,total:789,quantity:1};
if(api.resolve(row,categories,examples).id!==null)throw Error('manual clear');
row.category_id=4;
if(api.resolve(row,categories,examples).id!==4)throw Error('manual override');
row.category_touched=false;row.catalog={category_id:6};
if(api.resolve(row,categories,examples).id!==6)throw Error('catalogue identity');
row.catalog=null;
if(api.resolve(row,categories,examples).id!==1)throw Error('new item');
if(row.price!==789||row.total!==789||row.quantity!==1)throw Error('receipt money');
console.log('ok');
'''
    assert subprocess.check_output(['node', '-e', 'global.window={App:{}};'+MODULE+script], text=True).strip() == 'ok'
