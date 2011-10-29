from __future__ import with_statement
from nose.tools import eq_
from xmlbuilder import XMLBuilder

def test_attr_access():
    xml = XMLBuilder('root')
    eq_(str(xml), "<root />")

t2 = \
"""<root>
    <t1 m="1">
        <t2 />
    </t1>
    <t3>mmm</t3>
</root>"""

def test_attr_access2():
    xml = XMLBuilder('root')
    xml.t1(m='1').t2
    xml.t3('mmm')
    
    eq_(str(xml), t2)

def test_with():
    x = XMLBuilder('root')
    x.some_tag
    x.some_tag_with_data('text', a='12')
    
    with x.some_tree(a='1'):
        with x.data:
            x.mmm
            [x.node(val=str(i)) for i in range(10)]
    
    etree_node = ~x # <= return xml.etree.ElementTree object
    print str(x) # <= string object
    
test_with()


